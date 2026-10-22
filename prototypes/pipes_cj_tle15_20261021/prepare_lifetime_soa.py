#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
src=(HERE/'candidate-indexed/solution.cj').read_text(); base=hashlib.sha256(src.encode()).hexdigest()
model=r'''public class CensoredLifetimeModel {
    private var recordBorn = FastIntVector()
    private var recordLength = FastIntVector()
    private var recordActive = FastIntVector()
    // No managed references in these numeric buffers; they never resize.
    private let cells = FastIntBuffer(1312)
    private let rates = FastFloatBuffer(656)
    private let nextCrossing = FastIntBuffer(8)
    private let lower = FastIntBuffer(8)
    private var clock: Int64 = 0
    private var referenceRate: Float64 = 0.0
    private var referenceError: Float64 = 0.0
    private var fitted: Bool = false

    public init() {
        recordBorn.add(0); recordLength.add(0); recordActive.add(0)
        for (i in 0..8) { nextCrossing[i] = 1 }
        lower[0] = 0; lower[1] = 16; lower[2] = 64; lower[3] = 256
        lower[4] = 1024; lower[5] = 4096; lower[6] = 16384; lower[7] = 65536
    }

    private func ageBin(age: Int64): Int64 {
        if (age < 1024) {
            if (age < 64) { return if (age < 16) { 0 } else { 1 } }
            return if (age < 256) { 2 } else { 3 }
        }
        if (age < 16384) { return if (age < 4096) { 4 } else { 5 } }
        return if (age < 65536) { 6 } else { 7 }
    }

    @OverflowWrapping
    private func predict(length: Int64, initialAge: Int64): LifetimeEstimate {
        var result = LifetimeEstimate()
        var age = initialAge
        let end = age + kHistoryWindow
        var bin = ageBin(age)
        let limits = lower.borrowData()
        let rateData = rates.borrowData()
        unsafe {
            while (age < end) {
                let next = if (bin + 1 < 8) { iMin(end, limits.read(bin + 1)) } else { end }
                let weight = Float64(next - age) / Float64(kHistoryWindow)
                let index = (length * 8 + bin) * 2
                result.mean += weight * rateData.read(index)
                result.error += weight * rateData.read(index + 1)
                age = next
                if (age < end) { bin++ }
            }
        }
        blackBox(this)
        return result
    }

    private func adjustedRatio(length: Int64, age: Int64): Float64 {
        if (!fitted) { return 1.0 }
        let prediction = predict(length, age)
        let margin = 2.0 * (prediction.error + referenceError)
        var supported = referenceRate
        if (prediction.mean - margin > referenceRate) { supported = prediction.mean - margin }
        else if (prediction.mean + margin < referenceRate) { supported = prediction.mean + margin }
        return fMin(fMax(supported / referenceRate, 0.5), 2.0)
    }

    @OverflowWrapping
    public func advance(): Unit {
        clock++
        let born = recordBorn.borrowData()
        let length = recordLength.borrowData()
        let active = recordActive.borrowData()
        let count = recordBorn.size
        let crossing = nextCrossing.borrowData()
        let limits = lower.borrowData()
        let cellData = cells.borrowData()
        unsafe {
            for (bin in 1..8) {
                var cursor = crossing.read(bin)
                let threshold = limits.read(bin)
                while (cursor < count && clock - born.read(cursor) >= threshold) {
                    let birth = born.read(cursor)
                    let size = length.read(cursor)
                    let alive = active.read(cursor)
                    cursor++
                    if (alive == 0) { continue }
                    let previous = (size * 8 + bin - 1) * 4
                    cellData.write(previous, cellData.read(previous) + threshold - limits.read(bin - 1))
                    cellData.write(previous + 2, cellData.read(previous + 2) - 1)
                    cellData.write(previous + 1, cellData.read(previous + 1) - birth)
                    let current = (size * 8 + bin) * 4
                    cellData.write(current + 2, cellData.read(current + 2) + 1)
                    cellData.write(current + 1, cellData.read(current + 1) + birth)
                }
                crossing.write(bin, cursor)
            }
        }
        blackBox(this)
    }

    @OverflowWrapping
    public func observeBirth(length: Int64): Unit {
        recordBorn.add(clock); recordLength.add(length); recordActive.add(1)
        let cellData = cells.borrowData()
        let index = length * 8 * 4
        unsafe {
            cellData.write(index + 2, cellData.read(index + 2) + 1)
            cellData.write(index + 1, cellData.read(index + 1) + clock)
        }
        blackBox(this)
    }

    @OverflowWrapping
    public func observeDeletion(pid: Int64): Unit {
        let birth = recordBorn[pid]
        let length = recordLength[pid]
        let age = clock - birth
        let bin = ageBin(age)
        let index = (length * 8 + bin) * 4
        let cellData = cells.borrowData()
        let limits = lower.borrowData()
        unsafe {
            cellData.write(index, cellData.read(index) + age - limits.read(bin))
            cellData.write(index + 2, cellData.read(index + 2) - 1)
            cellData.write(index + 1, cellData.read(index + 1) - birth)
            let eventBin = ageBin(if (age == 0) { 0 } else { age - 1 })
            let eventIndex = (length * 8 + eventBin) * 4 + 3
            cellData.write(eventIndex, cellData.read(eventIndex) + 1)
        }
        recordActive[pid] = 0
        blackBox(this)
    }

    @OverflowWrapping
    public func fit(priorHazard: Float64): Bool {
        fitted = false
        if (!(priorHazard > 0.0)) { return false }
        let priorEvents: Float64 = 8.0
        let cellData = cells.borrowData()
        let rateData = rates.borrowData()
        let limits = lower.borrowData()
        unsafe {
            for (bin in 0..8) {
                let fitBinLower = limits.read(bin)
                var pooledExposure: Float64 = 0.0
                var pooledDeaths: Float64 = 0.0
                for (length in 1..41) {
                    let index = (length * 8 + bin) * 4
                    let active = cellData.read(index + 2)
                    let fitOutstanding: Int64 = if (active == 0) { 0 } else { active * (clock - fitBinLower) - cellData.read(index + 1) }
                    let fitExposure = cellData.read(index) + fitOutstanding
                    pooledExposure += Float64(fitExposure)
                    pooledDeaths += Float64(cellData.read(index + 3))
                }
                let pooledDenominator = pooledExposure + priorEvents / priorHazard
                let pooledRate = (pooledDeaths + priorEvents) / pooledDenominator
                let pooledError = sqrt(pooledDeaths + priorEvents) / pooledDenominator
                let borrowedExposure = priorEvents / pooledRate
                for (length in 1..41) {
                    let index = (length * 8 + bin) * 4
                    let active = cellData.read(index + 2)
                    let fitOutstanding: Int64 = if (active == 0) { 0 } else { active * (clock - fitBinLower) - cellData.read(index + 1) }
                    let fitExposure = cellData.read(index) + fitOutstanding
                    let denominator = Float64(fitExposure) + borrowedExposure
                    let shape = Float64(cellData.read(index + 3)) + priorEvents
                    let rateIndex = (length * 8 + bin) * 2
                    rateData.write(rateIndex, shape / denominator)
                    rateData.write(rateIndex + 1, sqrt(shape) / denominator + borrowedExposure / denominator * pooledError)
                }
            }
        }
        var sumRate: Float64 = 0.0
        var sumError: Float64 = 0.0
        var population: Int64 = 0
        unsafe {
            for (length in 1..41) {
                for (bin in 0..8) {
                    let index = (length * 8 + bin) * 4
                    let active = cellData.read(index + 2)
                    if (active == 0) { continue }
                    let meanAge = clock - cellData.read(index + 1) / active
                    let prediction = predict(length, meanAge)
                    sumRate += Float64(active) * prediction.mean
                    sumError += Float64(active) * prediction.error
                    population += active
                }
            }
        }
        blackBox(this)
        if (population == 0) { return false }
        referenceRate = sumRate / Float64(population)
        referenceError = sumError / Float64(population)
        fitted = referenceRate > 0.0
        return fitted
    }

    public func existingRisk(pid: Int64): Float64 {
        return adjustedRatio(recordLength[pid], clock - recordBorn[pid])
    }
    public func newRisk(length: Int64): Float64 { return adjustedRatio(length, 0) }
}
'''
a=src.index('public class CensoredLifetimeModel {'); b=src.index('// Fixed-capacity owner',a)
src=src[:a]+model+'\n'+src[b:]
out=HERE/'candidate-soa';out.mkdir(exist_ok=True);(out/'solution.cj').write_text(src)
(out/'source.json').write_text(json.dumps(dict(base_sha256=base,source_sha256=hashlib.sha256(src.encode()).hexdigest(),changes=['Lifetime scalar numeric storage, no managed struct arrays or per-cell wrappers.','Same event/age-bin updates, FP formulas/loop order/rounding points; fixed buffer borrows fenced after last use.','Dynamic record buffers borrowed only in advance, which never adds records.','Integer bounds from <=200000 commands,<=40 length; worst cumulative exposure and birthsum <40000000000.']),indent=2)+'\n')
print(out)
