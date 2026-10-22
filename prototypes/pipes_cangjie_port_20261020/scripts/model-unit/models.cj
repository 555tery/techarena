package pipes

import std.collection.*
import std.math.*

public let kDigLength: Int64 = 20
public let kHistoryWindow: Int64 = 2048
public let kUnfitPenaltyScale: Int64 = 60
public let kPrimalGapValueCap: Int64 = 512
public let kRightEdgeMaxPipeLength: Int64 = 4
public let kSameLengthRightRun: Int64 = 46
public let kMcHistory: Int64 = 256
public let kMcDepth: Int64 = 4
public let kMcTrials: Int64 = 12
public let kMcDecisionBudget: Int64 = 32
public let kMcMaxGaps: Int64 = 64
public let kMcMaxActivePipes: Int64 = 4096
public let kMcMinimumMeanSavingM: Int64 = 1

public struct Observation {
    public var kind: Int64 = 0
    public var value: Int64 = 0
    public init() {}
    public init(kind: Int64, value: Int64) {
        this.kind = kind
        this.value = value
    }
}

public struct SimPipe {
    public var pid: Int64 = 0
    public var start: Int64 = 0
    public var length: Int64 = 0
    public var sizeCohort: Int64 = 0
    public init() {}
    public init(pid: Int64, start: Int64, length: Int64, sizeCohort: Int64) {
        this.pid = pid
        this.start = start
        this.length = length
        this.sizeCohort = sizeCohort
    }
}

public struct SimGap {
    public var end: Int64 = 0
    public var cohort: Int64 = -1
    public init() {}
    public init(end: Int64, cohort: Int64) {
        this.end = end
        this.cohort = cohort
    }
}

public struct GapCandidate {
    public var start: Int64 = 0
    public var score: Int64 = 0
    public init() {}
    public init(start: Int64, score: Int64) {
        this.start = start
        this.score = score
    }
}

public func predictNextGeometricSize(history: Ring<Int64>, currentLength: Int64): Int64 {
    if (history.size == 0 || history.back() != currentLength) { return 0 }
    var index = history.size - 1
    let runSizes = Array<Int64>(3, repeat: 0)
    let runCounts = Array<Int64>(3, repeat: 0)
    var runIndex: Int64 = 0
    while (index >= 0 && runIndex < 3) {
        let size = history.get(index)
        var count: Int64 = 0
        while (index >= 0 && history.get(index) == size) {
            count++
            index--
        }
        runSizes[runIndex] = size
        runCounts[runIndex] = count
        runIndex++
    }
    if (runIndex < 3 || runSizes[0] != currentLength ||
        runCounts[0] < kSameLengthRightRun || runCounts[1] < kSameLengthRightRun ||
        runCounts[2] < kSameLengthRightRun) { return 0 }
    let previous = runSizes[1]
    let beforePrevious = runSizes[2]
    if (!(beforePrevious < previous && previous < currentLength)) { return 0 }
    let observed = currentLength * beforePrevious
    let expected = previous * previous
    let error = if (observed > expected) { observed - expected } else { expected - observed }
    if (2 * error > beforePrevious) { return 0 }
    let predicted = (currentLength * previous + beforePrevious / 2) / beforePrevious
    if (predicted <= currentLength || predicted > 40) { return 0 }
    return predicted
}

public func trendAlignedHighSide(history: Ring<Int64>, currentLength: Int64,
    gapStart: Int64, gapEnd: Int64, fallbackHighSide: Bool): Bool {
    let predictedLength = predictNextGeometricSize(history, currentLength)
    if (predictedLength <= currentLength || gapEnd - gapStart <= currentLength) {
        return fallbackHighSide
    }
    let lowResidue = (gapStart + currentLength) % predictedLength
    let highResidue = gapStart % predictedLength
    let lowScore = iMin(lowResidue, predictedLength - lowResidue)
    let highScore = iMin(highResidue, predictedLength - highResidue)
    if (highScore != lowScore) { return highScore < lowScore }
    return fallbackHighSide
}

public class RolloutState {
    public var confidentRecentAddress: Bool = false
    public var gaps = OrderedMap<SimGap>(SimGap())
    public var active = ArrayList<SimPipe>()
    public var trenchLength: Int64 = 0
    public var nextPid: Int64 = 1
    public var recentLengths = Ring<Int64>(0)
    public var recentFrequency = Array<Int64>(41, repeat: 0)
    public var lengthOccurrenceCount = Array<Int64>(41, repeat: 0)
    public var removedLengthCohort = Array<Array<Int64>>(41, { _ => Array<Int64>(2, repeat: 0) })
    public var parityCohortMode: Bool = false
    public var runLeftDisabledBySmoothTrend: Bool = false
    public var alternatingDeleteMode: Bool = false
    public var predictedDeletedParity: Int64 = 1
    public var lastDeletedPid: Int64 = -1
    public var lastDeletedLength: Int64 = -1
    public var strideTwoDeleteTransitions: Int64 = 0

    public init() {}

    public func deepCopy(): RolloutState {
        let copy = RolloutState()
        copy.confidentRecentAddress = confidentRecentAddress
        copy.gaps = gaps.clone()
        for (pipe in active) { copy.active.add(pipe) }
        copy.trenchLength = trenchLength
        copy.nextPid = nextPid
        copy.recentLengths = recentLengths.clone()
        for (i in 0..41) {
            copy.recentFrequency[i] = recentFrequency[i]
            copy.lengthOccurrenceCount[i] = lengthOccurrenceCount[i]
            copy.removedLengthCohort[i][0] = removedLengthCohort[i][0]
            copy.removedLengthCohort[i][1] = removedLengthCohort[i][1]
        }
        copy.parityCohortMode = parityCohortMode
        copy.runLeftDisabledBySmoothTrend = runLeftDisabledBySmoothTrend
        copy.alternatingDeleteMode = alternatingDeleteMode
        copy.predictedDeletedParity = predictedDeletedParity
        copy.lastDeletedPid = lastDeletedPid
        copy.lastDeletedLength = lastDeletedLength
        copy.strideTwoDeleteTransitions = strideTwoDeleteTransitions
        return copy
    }

    public func hasSteadySizeTrend(): Bool {
        if (recentLengths.size < 128) { return false }
        let distinctLengths = Array<Int64>(3, repeat: 0)
        var distinctCount: Int64 = 0
        var previous: Int64 = -1
        var index = recentLengths.size - 1
        while (index >= 0) {
            let length = recentLengths.get(index)
            index--
            if (length == previous) { continue }
            distinctLengths[distinctCount] = length
            distinctCount++
            previous = length
            if (distinctCount == 3) { break }
        }
        if (distinctCount < 3) { return false }
        return distinctLengths[0] - distinctLengths[1] == distinctLengths[1] - distinctLengths[2]
    }

    public func hasSameLengthRecentRun(length: Int64): Bool {
        if (recentLengths.size < kSameLengthRightRun) { return false }
        for (seen in 0..kSameLengthRightRun) {
            if (recentLengths.get(recentLengths.size - 1 - seen) != length) { return false }
        }
        return true
    }

    public func hasSmoothSizeTrendWith(currentLength: Int64): Bool {
        if (recentLengths.size == 0) { return false }
        let currentRunAlreadyInHistory = recentLengths.back() == currentLength
        let priorRunLengths = Array<Int64>(2, repeat: 0)
        var distinctCount: Int64 = 0
        var firstRun = true
        var lastRunLength: Int64 = -1
        var index = recentLengths.size - 1
        while (index >= 0) {
            let length = recentLengths.get(index)
            index--
            if (firstRun) {
                firstRun = false
                lastRunLength = length
                if (!currentRunAlreadyInHistory) {
                    priorRunLengths[distinctCount] = length
                    distinctCount++
                }
                continue
            }
            if (length == lastRunLength) { continue }
            lastRunLength = length
            priorRunLengths[distinctCount] = length
            distinctCount++
            if (distinctCount == 2) { break }
        }
        if (distinctCount < 2) { return false }
        return currentLength - priorRunLengths[0] == priorRunLengths[0] - priorRunLengths[1]
    }

    public func placementStart(gap: SimGap, start: Int64, length: Int64, highSide: Bool): Int64 {
        return if (highSide) { gap.end - length } else { start }
    }

    public func addFreeGap(initialStart: Int64, initialEnd: Int64, initialCohort: Int64): Unit {
        var start = initialStart
        var end = initialEnd
        var cohort = initialCohort
        if (start >= end) { return }
        var it = gaps.lower(Key(start))
        let previous = if (it == 0) { gaps.last() } else { gaps.prev(it) }
        if (previous != 0 && gaps.value(previous).end >= start) {
            if (gaps.value(previous).cohort != cohort) { cohort = -1 }
            start = gaps.key(previous).a
            end = iMax(end, gaps.value(previous).end)
            gaps.eraseNode(previous)
            it = gaps.lower(Key(start))
        }
        while (it != 0 && gaps.key(it).a <= end) {
            let gap = gaps.value(it)
            if (gap.cohort != cohort) { cohort = -1 }
            end = iMax(end, gap.end)
            let next = gaps.next(it)
            gaps.eraseNode(it)
            it = next
        }
        gaps.put(Key(start), SimGap(end, cohort))
    }

    public func splitGap(gapStart: Int64, length: Int64, highSide: Bool): Unit {
        let it = gaps.find(Key(gapStart))
        if (it == 0) { return }
        let start = gaps.key(it).a
        let gap = gaps.value(it)
        let pipeStart = placementStart(gap, start, length, highSide)
        gaps.eraseNode(it)
        if (start < pipeStart) { addFreeGap(start, pipeStart, gap.cohort) }
        let pipeEnd = pipeStart + length
        if (pipeEnd < gap.end) { addFreeGap(pipeEnd, gap.end, gap.cohort) }
    }

    public func recordLength(length: Int64): Unit {
        recentLengths.pushBack(length)
        recentFrequency[length]++
        if (recentLengths.size > kHistoryWindow) {
            recentFrequency[recentLengths.get(0)]--
            recentLengths.popFront()
        }
    }

    public func fitScore(gapLength: Int64, length: Int64): Int64 {
        let slack = gapLength - length
        var score = slack * recentLengths.size
        if (slack > 0 && slack <= 40) {
            var misses: Int64 = 0
            for (request in (slack + 1)..41) { misses += recentFrequency[request] }
            score += kUnfitPenaltyScale * misses
        }
        return score
    }

    public func bestGap(length: Int64, highSide: Bool, sizeCohort: Int64): Option<Int64> {
        var hasPreferred = false
        if (parityCohortMode) {
            var it = gaps.first()
            while (it != 0) {
                let start = gaps.key(it).a
                let gap = gaps.value(it)
                if (gap.end - start >= length && gap.cohort == sizeCohort) {
                    hasPreferred = true
                    break
                }
                it = gaps.next(it)
            }
        }
        var found = false
        var bestStart: Int64 = 0
        var bestScore: Int64 = Int64.Max
        let consideredLengths = OrderedMap<Int64>(0)
        var it = gaps.first()
        while (it != 0) {
            let start = gaps.key(it).a
            let gap = gaps.value(it)
            it = gaps.next(it)
            let gapLength = gap.end - start
            if (gapLength < length) { continue }
            if (parityCohortMode && (if (hasPreferred) { gap.cohort != sizeCohort } else { gap.cohort >= 0 })) { continue }
            let alreadyConsidered = consideredLengths.find(Key(gapLength)) != 0
            consideredLengths.put(Key(gapLength), 0)
            if (alreadyConsidered && !(confidentRecentAddress && highSide)) { continue }
            let score = fitScore(gapLength, length)
            if (!found || score < bestScore || (score == bestScore &&
                ((highSide && start > bestStart) || (!highSide && start < bestStart)))) {
                found = true
                bestStart = start
                bestScore = score
            }
        }
        return if (found) { Some(bestStart) } else { None }
    }

    public func appendPipe(length: Int64, start: Int64, sizeCohort: Int64): Unit {
        active.add(SimPipe(nextPid, start, length, sizeCohort))
        nextPid++
        lengthOccurrenceCount[length]++
        recordLength(length)
    }

    public func placeAtCandidate(gapStart: Int64, length: Int64, highSide: Bool): Unit {
        let it = gaps.find(Key(gapStart))
        if (it == 0) { return }
        let sizeCohort = lengthOccurrenceCount[length] % 2
        let start = placementStart(gaps.value(it), gapStart, length, highSide)
        splitGap(gapStart, length, highSide)
        appendPipe(length, start, sizeCohort)
    }

    public func place(length: Int64): Unit {
        let sizeCohort = lengthOccurrenceCount[length] % 2
        if (hasSmoothSizeTrendWith(length)) { runLeftDisabledBySmoothTrend = true }
        let sameSizeRun = hasSameLengthRecentRun(length)
        let geometricLaneActive = !runLeftDisabledBySmoothTrend && sameSizeRun
        let rearmReverse = runLeftDisabledBySmoothTrend && sameSizeRun && alternatingDeleteMode
        let runLeftActive = geometricLaneActive || rearmReverse
        let highSide = if (runLeftActive) {
            if (rearmReverse) { sizeCohort == 0 } else { (nextPid & 1) == 0 }
        } else if (alternatingDeleteMode) { (nextPid & 1) != predictedDeletedParity
        } else if (parityCohortMode) { sizeCohort == 0
        } else { length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length) }
        var start: Int64 = -1
        if (let Some(gapStart) <- bestGap(length, highSide, sizeCohort)) {
            let it = gaps.find(Key(gapStart))
            let gap = gaps.value(it)
            let selectedHighSide = if (geometricLaneActive) {
                trendAlignedHighSide(recentLengths, length, gaps.key(it).a, gap.end, highSide)
            } else { highSide }
            start = placementStart(gap, gapStart, length, selectedHighSide)
            splitGap(gapStart, length, selectedHighSide)
        }
        if (start < 0) {
            var tail: Int64 = 0
            if (!gaps.isEmpty()) {
                let last = gaps.last()
                if (gaps.value(last).end == trenchLength) { tail = last }
            }
            var tailCohort: Int64 = if (parityCohortMode) { sizeCohort } else { -1 }
            var preserveForeignTail = false
            if (parityCohortMode && tail != 0) {
                tailCohort = gaps.value(tail).cohort
                preserveForeignTail = tailCohort >= 0 && tailCohort != sizeCohort
                if (preserveForeignTail) { tailCohort = sizeCohort }
            }
            let tailStart = if (tail == 0 || preserveForeignTail) { trenchLength } else { gaps.key(tail).a }
            let tailLength = trenchLength - tailStart
            let deficit = iMax(0, length - tailLength)
            let digs = (deficit + kDigLength - 1) / kDigLength
            trenchLength += digs * kDigLength
            if (tail != 0 && !preserveForeignTail) { gaps.eraseNode(tail) }
            if (parityCohortMode && highSide && !preserveForeignTail) {
                start = trenchLength - length
                if (tailStart < start) { addFreeGap(tailStart, start, tailCohort) }
            } else {
                start = tailStart
                let remainderStart = start + length
                if (remainderStart < trenchLength) { addFreeGap(remainderStart, trenchLength, tailCohort) }
            }
        }
        appendPipe(length, start, sizeCohort)
    }

    public func recordDeletionPattern(pid: Int64, length: Int64): Unit {
        if (lastDeletedPid >= 0 && lastDeletedLength == length && pid == lastDeletedPid + 2) {
            strideTwoDeleteTransitions++
        } else {
            strideTwoDeleteTransitions = 0
            alternatingDeleteMode = false
        }
        if (strideTwoDeleteTransitions >= 7) {
            alternatingDeleteMode = true
            predictedDeletedParity = pid & 1
        }
        lastDeletedPid = pid
        lastDeletedLength = length
    }

    public func removeByRank(rankFromNewestPermille: Int64): Unit {
        if (active.size == 0) { return }
        let n = active.size
        let rankFromNewest: Int64 = if (n <= 1) { 0 } else { rankFromNewestPermille * (n - 1) / 1000 }
        let index = n - 1 - iMin(rankFromNewest, n - 1)
        let pipe = active[index]
        active.remove(at: index)
        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort)
        recordDeletionPattern(pipe.pid, pipe.length)
        removedLengthCohort[pipe.length][pipe.sizeCohort]++
        let totalForLength = removedLengthCohort[pipe.length][0] + removedLengthCohort[pipe.length][1]
        let dominantForLength = iMax(removedLengthCohort[pipe.length][0], removedLengthCohort[pipe.length][1])
        if (totalForLength >= 8 && dominantForLength * 100 >= totalForLength * 85 && hasSteadySizeTrend()) {
            parityCohortMode = true
        }
    }

    public func apply(event: Observation): Unit {
        if (event.kind > 0) { place(event.value) }
        else if (event.kind < 0) { removeByRank(event.value) }
    }
}

public struct Pipe {
    public var start: Int64 = 0
    public var length: Int64 = 0
    public var active: Bool = false
    public var sizeCohort: Int64 = 0
    public init() {}
    public init(start: Int64, length: Int64, active: Bool, sizeCohort: Int64) {
        this.start = start
        this.length = length
        this.active = active
        this.sizeCohort = sizeCohort
    }
}

private struct LifetimeRecord {
    public var born: Int64 = 0
    public var length: Int64 = 0
    public var active: Bool = false
    public init() {}
    public init(born: Int64, length: Int64, active: Bool) {
        this.born = born
        this.length = length
        this.active = active
    }
}

private struct LifetimeCell {
    public var completedExposure: Int64 = 0
    public var birthSum: Int64 = 0
    public var active: Int64 = 0
    public var deaths: Int64 = 0
    public init() {}
}

private struct LifetimeEstimate {
    public var mean: Float64 = 0.0
    public var error: Float64 = 0.0
    public init() {}
    public init(mean: Float64, error: Float64) {
        this.mean = mean
        this.error = error
    }
}

public class CensoredLifetimeModel {
    private let lower: Array<Int64> = [0, 16, 64, 256, 1024, 4096, 16384, 65536]
    private var records = ArrayList<LifetimeRecord>([LifetimeRecord()])
    private var cells = Array<Array<LifetimeCell>>(41, { _ => Array<LifetimeCell>(8, repeat: LifetimeCell()) })
    private var rates = Array<Array<LifetimeEstimate>>(41, { _ => Array<LifetimeEstimate>(8, repeat: LifetimeEstimate()) })
    private var nextCrossing = Array<Int64>(8, repeat: 1)
    private var clock: Int64 = 0
    private var referenceRate: Float64 = 0.0
    private var referenceError: Float64 = 0.0
    private var fitted: Bool = false

    public init() {}

    private func ageBin(age: Int64): Int64 {
        var bin: Int64 = 0
        while (bin + 1 < 8 && age >= lower[bin + 1]) { bin++ }
        return bin
    }

    private func enter(record: LifetimeRecord, bin: Int64): Unit {
        var cell = cells[record.length][bin]
        cell.active++
        cell.birthSum += record.born
        cells[record.length][bin] = cell
    }

    private func leave(record: LifetimeRecord, bin: Int64, age: Int64): Unit {
        var cell = cells[record.length][bin]
        cell.completedExposure += age - lower[bin]
        cell.active--
        cell.birthSum -= record.born
        cells[record.length][bin] = cell
    }

    private func exposure(cell: LifetimeCell, bin: Int64): Int64 {
        let outstanding: Int64 = if (cell.active == 0) { 0 } else { cell.active * (clock - lower[bin]) - cell.birthSum }
        return cell.completedExposure + outstanding
    }

    private func predict(length: Int64, initialAge: Int64): LifetimeEstimate {
        var result = LifetimeEstimate()
        var age = initialAge
        let end = age + kHistoryWindow
        var bin = ageBin(age)
        while (age < end) {
            let next = if (bin + 1 < 8) { iMin(end, lower[bin + 1]) } else { end }
            let weight = Float64(next - age) / Float64(kHistoryWindow)
            let rate = rates[length][bin]
            result.mean += weight * rate.mean
            result.error += weight * rate.error
            age = next
            if (age < end) { bin++ }
        }
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

    public func advance(): Unit {
        clock++
        for (bin in 1..8) {
            var cursor = nextCrossing[bin]
            while (cursor < records.size && clock - records[cursor].born >= lower[bin]) {
                let record = records[cursor]
                cursor++
                if (!record.active) { continue }
                leave(record, bin - 1, lower[bin])
                enter(record, bin)
            }
            nextCrossing[bin] = cursor
        }
    }

    public func observeBirth(length: Int64): Unit {
        let record = LifetimeRecord(clock, length, true)
        records.add(record)
        enter(record, 0)
    }

    public func observeDeletion(pid: Int64): Unit {
        var record = records[pid]
        let age = clock - record.born
        leave(record, ageBin(age), age)
        let eventBin = ageBin(if (age == 0) { 0 } else { age - 1 })
        var cell = cells[record.length][eventBin]
        cell.deaths++
        cells[record.length][eventBin] = cell
        record.active = false
        records[pid] = record
    }

    public func fit(priorHazard: Float64): Bool {
        fitted = false
        if (!(priorHazard > 0.0)) { return false }
        let priorEvents: Float64 = 8.0
        for (bin in 0..8) {
            var pooledExposure: Float64 = 0.0
            var pooledDeaths: Float64 = 0.0
            for (length in 1..41) {
                pooledExposure += Float64(exposure(cells[length][bin], bin))
                pooledDeaths += Float64(cells[length][bin].deaths)
            }
            let pooledDenominator = pooledExposure + priorEvents / priorHazard
            let pooledRate = (pooledDeaths + priorEvents) / pooledDenominator
            let pooledError = sqrt(pooledDeaths + priorEvents) / pooledDenominator
            for (length in 1..41) {
                let cell = cells[length][bin]
                let borrowedExposure = priorEvents / pooledRate
                let denominator = Float64(exposure(cell, bin)) + borrowedExposure
                let shape = Float64(cell.deaths) + priorEvents
                rates[length][bin] = LifetimeEstimate(shape / denominator,
                    sqrt(shape) / denominator + borrowedExposure / denominator * pooledError)
            }
        }
        var sumRate: Float64 = 0.0
        var sumError: Float64 = 0.0
        var population: Int64 = 0
        for (length in 1..41) {
            for (bin in 0..8) {
                let cell = cells[length][bin]
                if (cell.active == 0) { continue }
                let meanAge = clock - cell.birthSum / cell.active
                let prediction = predict(length, meanAge)
                sumRate += Float64(cell.active) * prediction.mean
                sumError += Float64(cell.active) * prediction.error
                population += cell.active
            }
        }
        if (population == 0) { return false }
        referenceRate = sumRate / Float64(population)
        referenceError = sumError / Float64(population)
        fitted = referenceRate > 0.0
        return fitted
    }

    public func existingRisk(pid: Int64): Float64 {
        let record = records[pid]
        return adjustedRatio(record.length, clock - record.born)
    }

    public func newRisk(length: Int64): Float64 {
        return adjustedRatio(length, 0)
    }
}
