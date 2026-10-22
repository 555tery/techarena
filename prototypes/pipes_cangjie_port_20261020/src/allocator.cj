package pipes

import std.collection.*

// Native online allocator. OrderedMap node 0 is the C++ end iterator.
public class Allocator {
    public var emit = true
    public var releaseEpoch: Int64 = 0
    public var recencyDifferentSelections: Int64 = 0
    public var gapFreedAt = OrderedMap<Int64>(0)
    public var freeBySizeAge = OrderedMap<Int64>(0)
    public var freeByStart = OrderedMap<Int64>(0)
    public var activeByEnd = OrderedMap<Int64>(0)
    public var freeBySize = OrderedMap<Int64>(0)
    public var gapCohort = OrderedMap<Int64>(0)
    public var freeBySizeCohort = [OrderedMap<Int64>(0), OrderedMap<Int64>(0)]
    public var freeBySizeShared = OrderedMap<Int64>(0)
    public var pipes = ArrayList<Pipe>()
    public var trenchLength: Int64 = 0
    public var completedPlacementRuns = Ring<Key>(Key(0))
    public var observedRunLength: Int64 = -1
    public var observedRunCount: Int64 = 0
    public var cohortSlabActive = false
    public var cohortSlabExpanded = false
    public var cohortSlabExpectedCount: Int64 = 0
    public var cohortSlabDeleteParity: Int64 = 0
    public var cohortSlabDeleteCount: Int64 = 0
    public var cohortSlabDeletedUsed: Int64 = 0
    public var cohortSlabSurvivorUsed: Int64 = 0
    public var cohortSlabGapSinkRemaining: Int64 = 0
    public var cohortSlabTailPipeCount: Int64 = 0
    public var cohortSlabUsed: Int64 = 0
    public var cohortSlabBase: Int64 = 0
    public var cohortSlabEnd: Int64 = 0
    public var recentLengths = Ring<Int64>(0)
    public var recentFrequency = Array<Int64>(41, repeat: 0)
    public var lengthOccurrenceCount = Array<Int64>(41, repeat: 0)
    public var removedLengthCohort = Array<Array<Int64>>(41, {_ => Array<Int64>(2, repeat: 0)})
    public var parityCohortMode = false
    public var runLeftDisabledBySmoothTrend = false
    public var alternatingDeleteMode = false
    public var predictedDeletedParity: Int64 = 1
    public var lastDeletedPid: Int64 = -1
    public var lastDeletedLength: Int64 = -1
    public var strideTwoDeleteTransitions: Int64 = 0
    public var activeFenwick = Array<Int64>(200001, repeat: 0)
    public var activePipeCount: Int64 = 0
    public var observedHistory = Ring<Observation>(Observation())
    public var mcDecisionsUsed: Int64 = 0
    public var mcRolloutsRun: Int64 = 0
    public var recentDeleteRanksPermille = Ring<Int64>(0)
    public var lifoLaneDisabledForScale = false
    public var primalGapCounts = Array<Int64>(kPrimalGapValueCap + 2, repeat: 0)
    public var primalEventHistory = Array<Int64>(256, repeat: 0)
    public var primalRecentRequests = Array<Int64>(41, repeat: 0)
    public var primalGapValue = Array<Float64>(kPrimalGapValueCap + 1, repeat: 0.0)
    public var primalEventPosition: Int64 = 0
    public var primalRecentDeletes: Int64 = 0
    public var primalStep: Int64 = 0
    public var primalModelStep: Int64 = 0
    public var primalComputedLimit: Int64 = 0
    public var primalModelDirty = true
    public var primalScoredDecisions: Int64 = 0
    public var primalChangedSelections: Int64 = 0
    public var primalCapFallbacks: Int64 = 0
    public var primalModelRebuilds: Int64 = 0
    public var primalFirstActivationEvent: Int64 = 0
    public var activeRunFirstPid: Int64 = 1
    public var activeRunDeleteParityCount = Array<Int64>(2, repeat: 0)
    public var lastCompletedDeleteRelativeParity: Int64 = -1
    public var previousCompletedDeleteRelativeParity: Int64 = -1
    public var lifetimeModel = CensoredLifetimeModel()
    public var causalRequestRate = Array<Float64>(41, repeat: 0.0)
    public var causalGapValue = Array<Array<Float64>>(2, {_ => Array<Float64>(kPrimalGapValueCap + 1, repeat: 0.0)})
    public var causalBaseExpiry: Float64 = 0.0
    public var causalComputedLimit: Int64 = 0
    public var causalRiskReady = false
    public var expansionGateOpportunities: Int64 = 0
    public var expansionGatePasses: Int64 = 0
    public var unitProfileSuppressedExpansions: Int64 = 0
    public var randomState: Int64 = 1

    public init() { pipes.add(Pipe()) }

    public func hasLongAdditiveSizeTrend(currentLength: Int64): Bool {
        if (currentLength < 3 || currentLength >= 40 || observedRunCount < 46) { return false }
        let sizes = Array<Int64>(3, repeat: 0)
        let counts = Array<Int64>(3, repeat: 0)
        sizes[0] = currentLength
        counts[0] = observedRunCount
        var i = recentLengths.size - 1
        while (i >= 0 && recentLengths.get(i) == currentLength) { i-- }
        for (run in 1..3) {
            if (i < 0) { return false }
            let size = recentLengths.get(i)
            sizes[run] = size
            while (i >= 0 && recentLengths.get(i) == size) { counts[run]++; i-- }
            if (counts[run] < 46) { return false }
        }
        return sizes[0] == sizes[1] + 1 && sizes[1] == sizes[2] + 1
    }

    public func alignForNextAdditiveSize(length: Int64, gapStart: Int64, fallbackHighSide: Bool): Bool {
        let modulus = length + 1
        let lowResidue = (gapStart + length) % modulus
        let highResidue = gapStart % modulus
        let lowScore = iMin(lowResidue, modulus - lowResidue)
        let highScore = iMin(highResidue, modulus - highResidue)
        if (highScore != lowScore) { return highScore < lowScore }
        return fallbackHighSide
    }

    public func predictEarlyNextGeometricSize(currentLength: Int64): Int64 {
        if (completedPlacementRuns.size != 1 || observedRunCount < 46 || observedRunCount > 1024 ||
            !alternatingDeleteMode || strideTwoDeleteTransitions < 7 || activePipeCount > 4096 || freeByStart.size > 4096) { return 0 }
        let previous = completedPlacementRuns.back()
        if (previous.b < 46 || previous.a <= 0 || lastDeletedLength != previous.a || currentLength != previous.a * 2 || currentLength > 20) { return 0 }
        let predicted = currentLength * 2
        return if (predicted <= 40) { predicted } else { 0 }
    }

    public func hasLifoDeletionConfidence(): Bool {
        if (activePipeCount < 128 || recentDeleteRanksPermille.size < 48) { return false }
        var topFivePercent: Int64 = 0
        for (i in 0..recentDeleteRanksPermille.size) { if (recentDeleteRanksPermille.get(i) <= 50) { topFivePercent++ } }
        if (topFivePercent * 100 < recentDeleteRanksPermille.size * 80) { return false }
        var shortPlacements: Int64 = 0
        for (i in 0..recentLengths.size) { if (recentLengths.get(i) <= 8) { shortPlacements++ } }
        return recentLengths.size >= 64 && shortPlacements * 100 >= recentLengths.size * 90
    }

    public func hasYoungTailNeighbor(tailStart: Int64): Bool {
        let it = activeByEnd.find(Key(tailStart))
        return it != 0 && rankFromNewestPermille(activeByEnd.value(it)) <= 50
    }

    public func unitDominantRecentProfile(): Bool {
        if (recentLengths.size < 128) { return false }
        let window = iMin(recentLengths.size, 2048)
        var units: Int64 = 0
        for (seen in 0..window) { if (recentLengths.get(recentLengths.size - 1 - seen) == 1) { units++ } }
        return units * 100 >= window * 85
    }

    public func useLifoStackLane(currentLength: Int64): Bool {
        if (lifoLaneDisabledForScale || activePipeCount < 128 || currentLength > 8 || recentDeleteRanksPermille.size < 48) { return false }
        var topFivePercent: Int64 = 0
        for (i in 0..recentDeleteRanksPermille.size) { if (recentDeleteRanksPermille.get(i) <= 50) { topFivePercent++ } }
        if (topFivePercent * 100 < recentDeleteRanksPermille.size * 80) { return false }
        var shortPlacements: Int64 = 0
        for (i in 0..recentLengths.size) { if (recentLengths.get(i) <= 8) { shortPlacements++ } }
        return recentLengths.size >= 64 && shortPlacements * 100 >= recentLengths.size * 90
    }

    public func place(length: Int64): Unit {
        lifetimeModel.advance()
        if (observedRunLength != length) {
            if (observedRunCount > 0) {
                completedPlacementRuns.pushBack(Key(observedRunLength, observedRunCount))
                if (completedPlacementRuns.size > 8) { completedPlacementRuns.popFront() }
                let totalRemoved = activeRunDeleteParityCount[0] + activeRunDeleteParityCount[1]
                let dominant = iMax(activeRunDeleteParityCount[0], activeRunDeleteParityCount[1])
                if (totalRemoved >= 8 && dominant * 100 >= totalRemoved * 85) {
                    let absoluteParity: Int64 = if (activeRunDeleteParityCount[0] > activeRunDeleteParityCount[1]) { 0 } else { 1 }
                    previousCompletedDeleteRelativeParity = lastCompletedDeleteRelativeParity
                    lastCompletedDeleteRelativeParity = absoluteParity ^ (activeRunFirstPid & 1)
                } else {
                    previousCompletedDeleteRelativeParity = -1
                    lastCompletedDeleteRelativeParity = -1
                }
            }
            observedRunLength = length
            observedRunCount = 0
            activeRunFirstPid = pipes.size
            activeRunDeleteParityCount = Array<Int64>(2, repeat: 0)
            cohortSlabActive = false
            beginCohortSlab(length)
        }
        observedRunCount++
        let sizeCohort = lengthOccurrenceCount[length] % 2
        if (activePipeCount > kMcMaxActivePipes) { lifoLaneDisabledForScale = true }
        let lifoStackLane = length > kRightEdgeMaxPipeLength && useLifoStackLane(length)
        if (cohortSlabActive && cohortSlabUsed < cohortSlabExpectedCount) {
            let pid = pipes.size
            let predictedDeleted = (pid & 1) == cohortSlabDeleteParity
            var start: Int64 = -1
            var tailPlacement = true
            if (!predictedDeleted && cohortSlabGapSinkRemaining > 0) {
                let reusableGap = bestFittingGapBefore(length, false, sizeCohort, cohortSlabBase)
                if (reusableGap != 0) {
                    start = consumeAtSide(reusableGap, length, false)
                    cohortSlabGapSinkRemaining--
                    tailPlacement = false
                }
            }
            if (tailPlacement) {
                if (predictedDeleted) {
                    start = cohortSlabBase + cohortSlabDeletedUsed * length
                    cohortSlabDeletedUsed++
                } else {
                    start = cohortSlabBase + (cohortSlabDeleteCount + cohortSlabSurvivorUsed) * length
                    cohortSlabSurvivorUsed++
                }
            }
            var digs: Int64 = 0
            if (tailPlacement && !cohortSlabExpanded) {
                let missing = cohortSlabEnd - trenchLength
                digs = if (missing > 0) { (missing + kDigLength - 1) / kDigLength } else { 0 }
                trenchLength += digs * kDigLength
                cohortSlabExpanded = true
                let occupiedEnd = cohortSlabBase + cohortSlabTailPipeCount * length
                if (occupiedEnd < trenchLength) { addFreeGap(occupiedEnd, trenchLength, -1) }
            }
            printPlacement(digs, start)
            pipes.add(Pipe(start, length, true, sizeCohort))
            activeByEnd.put(Key(start + length), pid)
            fenwickAdd(pid, 1)
            activePipeCount++
            lengthOccurrenceCount[length]++
            recordLength(length)
            recordObservation(Observation(1, length))
            recordPrimalEvent(length)
            cohortSlabUsed++
            if (cohortSlabUsed >= cohortSlabExpectedCount) { cohortSlabActive = false }
            return
        }
        if (hasSmoothSizeTrendWith(length)) { runLeftDisabledBySmoothTrend = true }
        let sameSizeRun = hasSameLengthRecentRun(length)
        let geometricLaneActive = !runLeftDisabledBySmoothTrend && sameSizeRun
        let rearmReverse = runLeftDisabledBySmoothTrend && sameSizeRun && alternatingDeleteMode
        let runLeftActive = geometricLaneActive || rearmReverse
        let additiveNextAlignment = hasLongAdditiveSizeTrend(length)
        var highSide = lifoStackLane || (if (runLeftActive) {
            if (rearmReverse) { sizeCohort == 0 } else { (pipes.size & 1) == 0 }
        } else {
            if (alternatingDeleteMode) { (pipes.size & 1) != predictedDeletedParity }
            else { if (parityCohortMode) { sizeCohort == 0 } else { length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length) } }
        })
        var start: Int64 = -1
        let predictedNextClass = predictEarlyNextGeometricSize(length)
        var gap = bestFittingGap(length, highSide, sizeCohort)
        var counterfactualCapacityChoice = false
        if (predictedNextClass > length && (pipes.size & 1) != predictedDeletedParity) {
            let projectedChoice = chooseCounterfactualCapacityGap(length, predictedNextClass, highSide, sizeCohort, gap)
            if (projectedChoice[0] != 0) {
                gap = projectedChoice[0]
                highSide = projectedChoice[1] != 0
                counterfactualCapacityChoice = true
            }
        }
        if (gap != 0) {
            if (additiveNextAlignment) { highSide = alignForNextAdditiveSize(length, freeByStart.key(gap).a, highSide) }
            else if (geometricLaneActive) { highSide = trendAlignedHighSide(recentLengths, length, freeByStart.key(gap).a, freeByStart.value(gap), highSide) }
            if (lifoStackLane) { highSide = true }
            let selectedStart = if (additiveNextAlignment || counterfactualCapacityChoice) { freeByStart.key(gap).a }
                else { chooseGapWithRollout(length, highSide, sizeCohort, gap) }
            if (selectedStart >= 0) { gap = freeByStart.find(Key(selectedStart)) }
            start = consumeAtSide(gap, length, highSide)
        }
        var digs: Int64 = 0
        if (start < 0) {
            let tail = tailGap()
            var tailCohort: Int64 = if (parityCohortMode) { sizeCohort } else { -1 }
            var preserveForeignTail = false
            if (parityCohortMode && tail != 0) {
                tailCohort = gapCohort.value(gapCohort.find(Key(freeByStart.key(tail).a)))
                preserveForeignTail = tailCohort >= 0 && tailCohort != sizeCohort
                if (preserveForeignTail) { tailCohort = sizeCohort }
            }
            let tailStart = if (tail == 0 || preserveForeignTail) { trenchLength } else { freeByStart.key(tail).a }
            let tailLength = trenchLength - tailStart
            let deficit = iMax(0, length - tailLength)
            digs = (deficit + kDigLength - 1) / kDigLength
            let newLength = trenchLength + digs * kDigLength
            let baseOffsetGate = digs > 0 && activePipeCount > 4096 && !preserveForeignTail &&
                newLength - (tailStart + length) > 0 && hasLifoDeletionConfidence() && hasYoungTailNeighbor(tailStart)
            let suppressForUnitProfile = baseOffsetGate && unitDominantRecentProfile()
            let offsetGate = baseOffsetGate && !suppressForUnitProfile
            if (suppressForUnitProfile) { unitProfileSuppressedExpansions++ }
            if (digs > 0) { expansionGateOpportunities++ }
            if (offsetGate) { expansionGatePasses++ }
            if (tail != 0 && !preserveForeignTail) { eraseGap(tail) }
            trenchLength = newLength
            if ((parityCohortMode && highSide && !preserveForeignTail) || offsetGate) {
                start = trenchLength - length
                if (tailStart < start) { addFreeGap(tailStart, start, tailCohort) }
            } else {
                start = tailStart
                let remainderStart = start + length
                if (remainderStart < trenchLength) { addFreeGap(remainderStart, trenchLength, tailCohort) }
            }
        }
        printPlacement(digs, start)
        let pid = pipes.size
        pipes.add(Pipe(start, length, true, sizeCohort))
        activeByEnd.put(Key(start + length), pid)
        fenwickAdd(pid, 1)
        activePipeCount++
        lengthOccurrenceCount[length]++
        recordLength(length)
        recordObservation(Observation(1, length))
        recordPrimalEvent(length)
    }

    public func remove(pid: Int64): Unit {
        if (pid <= 0 || pid >= pipes.size || !pipes[pid].active) { printInvalidPidFallback(); return }
        lifetimeModel.advance()
        let rankPermille = rankFromNewestPermille(pid)
        var pipe = pipes[pid]
        lifetimeModel.observeDeletion(pid)
        activeByEnd.eraseKey(Key(pipe.start + pipe.length))
        if (emit) { answerRemoval(pipe.start) }
        pipe.active = false
        pipes[pid] = pipe
        fenwickAdd(pid, -1)
        activePipeCount--
        releaseEpoch++
        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort, releaseEpoch)
        recordDeletionPattern(pid, pipe.length)
        recordPrimalEvent(-1)
        if (pid >= activeRunFirstPid) { activeRunDeleteParityCount[pid & 1]++ }
        removedLengthCohort[pipe.length][pipe.sizeCohort]++
        let totalForLength = removedLengthCohort[pipe.length][0] + removedLengthCohort[pipe.length][1]
        let dominantForLength = iMax(removedLengthCohort[pipe.length][0], removedLengthCohort[pipe.length][1])
        if (totalForLength >= 8 && dominantForLength * 100 >= totalForLength * 85 && hasSteadySizeTrend()) { parityCohortMode = true }
        recordObservation(Observation(-1, rankPermille))
    }

    public func fenwickAdd(index: Int64, delta: Int64): Unit {
        var position = index
        while (position < activeFenwick.size) { activeFenwick[position] += delta; position += position & -position }
    }
    public func fenwickPrefix(index: Int64): Int64 {
        var sum: Int64 = 0
        var position = index
        while (position > 0) { sum += activeFenwick[position]; position -= position & -position }
        return sum
    }
    public func rankFromNewestPermille(pid: Int64): Int64 {
        if (activePipeCount <= 1) { return 0 }
        return (activePipeCount - fenwickPrefix(pid)) * 1000 / (activePipeCount - 1)
    }
    public func recordDeletionPattern(pid: Int64, length: Int64): Unit {
        if (lastDeletedPid >= 0 && lastDeletedLength == length && pid == lastDeletedPid + 2) { strideTwoDeleteTransitions++ }
        else { strideTwoDeleteTransitions = 0; alternatingDeleteMode = false }
        if (strideTwoDeleteTransitions >= 7) { alternatingDeleteMode = true; predictedDeletedParity = pid & 1 }
        lastDeletedPid = pid
        lastDeletedLength = length
    }

    public func beginCohortSlab(length: Int64): Unit {
        if (completedPlacementRuns.size < 2 || !alternatingDeleteMode) { return }
        let previous = completedPlacementRuns.get(completedPlacementRuns.size - 2)
        let last = completedPlacementRuns.back()
        if (!(previous.a < last.a && last.a < length) || lastDeletedLength != last.a) { return }
        let nextStep = length - last.a
        let predictedNextSize = length + nextStep
        if (predictedNextSize > 40) { return }
        let unitStaircase = last.a - previous.a == nextStep && nextStep == 1
        let countDifference = if (previous.b >= last.b) { previous.b - last.b } else { last.b - previous.b }
        let stableTolerance = iMax(10, iMax(previous.b, last.b) / 10)
        if (countDifference > stableTolerance) { return }
        let expectedCount = (previous.b + last.b) / 2
        if (expectedCount < 64) { return }
        var slabDeleteParity = predictedDeletedParity
        if (lastCompletedDeleteRelativeParity >= 0 && previousCompletedDeleteRelativeParity == lastCompletedDeleteRelativeParity) {
            slabDeleteParity = (activeRunFirstPid & 1) ^ lastCompletedDeleteRelativeParity
        }
        let firstPid = pipes.size
        let firstParity = firstPid & 1
        let deleteCount = expectedCount / 2 + (if ((expectedCount & 1) != 0 && firstParity == slabDeleteParity) { 1 } else { 0 })
        let survivorCount = expectedCount - deleteCount
        let firstOccurrenceParity = lengthOccurrenceCount[length] & 1
        let survivorSizeCohort = firstOccurrenceParity ^ (if ((firstPid & 1) == slabDeleteParity) { 1 } else { 0 })
        var reusableCapacity: Int64 = 0
        var it = freeByStart.first()
        while (it != 0) {
            let gapStart = freeByStart.key(it).a
            let gapEnd = freeByStart.value(it)
            let next = freeByStart.next(it)
            if (parityCohortMode) {
                let owner = gapCohort.value(gapCohort.find(Key(gapStart)))
                if (owner >= 0 && owner != survivorSizeCohort) { it = next; continue }
            }
            reusableCapacity = iMin(survivorCount, reusableCapacity + (gapEnd - gapStart) / length)
            if (reusableCapacity >= survivorCount) { break }
            it = next
        }
        let survivorGapCount = reusableCapacity
        let tailPipeCount = expectedCount - survivorGapCount
        let predictedFutureCapacity = deleteCount * length / predictedNextSize
        if (predictedFutureCapacity < 64) {
            if (!unitStaircase) { return }
            var existingFutureCapacity: Int64 = 0
            it = freeByStart.first()
            while (it != 0) {
                let gapStart = freeByStart.key(it).a
                let gapEnd = freeByStart.value(it)
                let next = freeByStart.next(it)
                if (parityCohortMode) {
                    let owner = gapCohort.value(gapCohort.find(Key(gapStart)))
                    if (owner >= 0 && owner != 0) { it = next; continue }
                }
                existingFutureCapacity += (gapEnd - gapStart) / predictedNextSize
                it = next
            }
            if (predictedFutureCapacity <= existingFutureCapacity) { return }
        }
        let rawLength = tailPipeCount * length
        let allocatedLength = ((rawLength + kDigLength - 1) / kDigLength) * kDigLength
        cohortSlabActive = true
        cohortSlabExpanded = false
        cohortSlabExpectedCount = expectedCount
        cohortSlabDeleteParity = slabDeleteParity
        cohortSlabDeleteCount = deleteCount
        cohortSlabDeletedUsed = 0
        cohortSlabSurvivorUsed = 0
        cohortSlabGapSinkRemaining = survivorGapCount
        cohortSlabTailPipeCount = tailPipeCount
        cohortSlabUsed = 0
        cohortSlabBase = trenchLength
        cohortSlabEnd = cohortSlabBase + allocatedLength
    }

    public func recordObservation(event: Observation): Unit {
        observedHistory.pushBack(event)
        if (observedHistory.size > kMcHistory) { observedHistory.popFront() }
        if (event.kind < 0) {
            recentDeleteRanksPermille.pushBack(event.value)
            if (recentDeleteRanksPermille.size > 64) { recentDeleteRanksPermille.popFront() }
        }
    }

    public func recordPrimalEvent(event: Int64): Unit {
        if (event > 0) { lifetimeModel.observeBirth(event) }
        let old = primalEventHistory[primalEventPosition]
        if (old > 0) {
            primalRecentRequests[old]--
            if (primalRecentRequests[old] == 0) { primalModelDirty = true }
        } else if (old < 0) {
            primalRecentDeletes--
            if (primalRecentDeletes == 0) { primalModelDirty = true }
        }
        primalEventHistory[primalEventPosition] = event
        primalEventPosition = (primalEventPosition + 1) % primalEventHistory.size
        if (event > 0) {
            if (primalRecentRequests[event] == 0) { primalModelDirty = true }
            primalRecentRequests[event]++
        } else if (event < 0) {
            if (primalRecentDeletes == 0) { primalModelDirty = true }
            primalRecentDeletes++
        }
        primalStep++
    }

    public func hasRecentPrimalDemand(): Bool {
        for (length in 1..primalRecentRequests.size) { if (primalRecentRequests[length] > 0) { return true } }
        return false
    }

    public func rebuildPrimalGapValues(maxGap: Int64): Unit {
        let rate = Array<Float64>(41, repeat: 0.0)
        var fitting = primalGapCounts[kPrimalGapValueCap + 1]
        var gap = kPrimalGapValueCap
        while (gap >= 1) {
            fitting += primalGapCounts[gap]
            if (gap <= 40) { rate[gap] = Float64(primalRecentRequests[gap]) / Float64(iMax(1, fitting)) }
            gap--
        }
        let expiry = 2.0 * Float64(primalRecentDeletes) / Float64(iMax(1, activePipeCount))
        primalGapValue = Array<Float64>(kPrimalGapValueCap + 1, repeat: 0.0)
        for (g in 1..=maxGap) {
            let top = iMin(g, 40)
            if (expiry == 0.0) {
                for (request in 1..=top) {
                    if (rate[request] > 0.0) { primalGapValue[g] = fMax(primalGapValue[g], Float64(request) + primalGapValue[g - request]) }
                }
                continue
            }
            let reward = Array<Float64>(41, repeat: 0.0)
            var active: Int64 = 0
            var numerator: Float64 = 0.0
            var denominator = expiry
            for (request in 1..=top) {
                let requestRate = rate[request]
                if (requestRate == 0.0) { continue }
                reward[request] = Float64(request) + primalGapValue[g - request]
                numerator += requestRate * reward[request]
                denominator += requestRate
                active = active | (1 << request)
            }
            var estimate = numerator / denominator
            while (true) {
                var removed = false
                for (request in 1..=top) {
                    let bit: Int64 = 1 << request
                    if ((active & bit) != 0 && reward[request] < estimate) {
                        numerator -= rate[request] * reward[request]
                        denominator -= rate[request]
                        active = active & (!bit)
                        removed = true
                    }
                }
                if (!removed) { break }
                estimate = numerator / denominator
            }
            primalGapValue[g] = fMin(fMax(estimate, 0.0), Float64(g))
        }
        causalRequestRate = rate
        causalBaseExpiry = expiry
        causalComputedLimit = 0
        causalRiskReady = !parityCohortMode && activePipeCount > kMcMaxActivePipes && expiry > 0.0 &&
            lifetimeModel.fit(expiry / (2.0 * Float64(primalEventHistory.size)))
        primalModelStep = primalStep
        primalComputedLimit = maxGap
        primalModelDirty = false
        primalModelRebuilds++
    }

    public func ensurePrimalGapValues(maxGap: Int64): Bool {
        if (maxGap <= 0 || maxGap > kPrimalGapValueCap) { return false }
        if (primalModelDirty || primalStep - primalModelStep >= 64 || maxGap > primalComputedLimit) { rebuildPrimalGapValues(maxGap) }
        return hasRecentPrimalDemand()
    }

    public func rebuildCausalGapValues(maxGap: Int64): Unit {
        for (model in 0..2) {
            let value = Array<Float64>(kPrimalGapValueCap + 1, repeat: 0.0)
            let expiry = causalBaseExpiry * (if (model == 0) { 0.5 } else { 2.0 })
            for (gap in 1..=maxGap) {
                let top = iMin(gap, 40)
                let reward = Array<Float64>(41, repeat: 0.0)
                var active: Int64 = 0
                var numerator: Float64 = 0.0
                var denominator = expiry
                for (request in 1..=top) {
                    let requestRate = causalRequestRate[request]
                    if (requestRate == 0.0) { continue }
                    reward[request] = Float64(request) + value[gap - request]
                    numerator += requestRate * reward[request]
                    denominator += requestRate
                    active = active | (1 << request)
                }
                var estimate = numerator / denominator
                while (true) {
                    var removed = false
                    for (request in 1..=top) {
                        let bit: Int64 = 1 << request
                        if ((active & bit) != 0 && reward[request] < estimate) {
                            numerator -= causalRequestRate[request] * reward[request]
                            denominator -= causalRequestRate[request]
                            active = active & (!bit)
                            removed = true
                        }
                    }
                    if (!removed) { break }
                    estimate = numerator / denominator
                }
                value[gap] = fMin(fMax(estimate, 0.0), Float64(gap))
            }
            causalGapValue[model] = value
        }
        causalComputedLimit = maxGap
    }

    public func causalValueAt(gap: Int64, expiryFactor: Float64): Float64 {
        let base = primalGapValue[gap]
        if (expiryFactor <= 1.0) { return base + 2.0 * (1.0 - expiryFactor) * (causalGapValue[0][gap] - base) }
        return base + (expiryFactor - 1.0) * (causalGapValue[1][gap] - base)
    }

    public func causalPrimalLoss(gap: Int64, length: Int64, highSide: Bool, modelLimit: Int64, freshRisk: Float64): Float64 {
        let start = freeByStart.key(gap).a
        let end = freeByStart.value(gap)
        let gapLength = end - start
        var leftRisk = 1.0
        var rightRisk = 1.0
        let left = activeByEnd.find(Key(start))
        if (left != 0) { leftRisk = lifetimeModel.existingRisk(activeByEnd.value(left)) }
        let right = activeByEnd.upper(Key(end))
        if (right != 0 && pipes[activeByEnd.value(right)].start == end) { rightRisk = lifetimeModel.existingRisk(activeByEnd.value(right)) }
        let originalFactor = 0.5 * (leftRisk + rightRisk)
        let remainingFactor = 0.5 * (freshRisk + (if (highSide) { leftRisk } else { rightRisk }))
        if (originalFactor == 1.0 && remainingFactor == 1.0) { return primalGapLoss(gapLength, length) }
        if (causalComputedLimit < modelLimit) { rebuildCausalGapValues(modelLimit) }
        return causalValueAt(gapLength, originalFactor) - causalValueAt(gapLength - length, remainingFactor)
    }

    public func chooseCausalLifetimeGap(candidates: ArrayList<Key>, length: Int64, highSide: Bool, baselineGap: Int64): Int64 {
        if (!causalRiskReady || alternatingDeleteMode || observedRunCount >= kSameLengthRightRun || candidates.size < 2) { return baselineGap }
        var challenger: Int64 = 0
        var challengerScore = Float64.Inf
        for (candidate in candidates) {
            let gapLength = candidate.a
            let representativeStart = candidate.b
            if (representativeStart == freeByStart.key(baselineGap).a) { continue }
            let score = primalGapLoss(gapLength, length)
            let strictlyBetter = score + 1e-9 < challengerScore
            let tied = !(challengerScore + 1e-9 < score) && !(score + 1e-9 < challengerScore)
            let addressPreferred = challenger != 0 && (if (highSide) { representativeStart > freeByStart.key(challenger).a } else { representativeStart < freeByStart.key(challenger).a })
            if (challenger == 0 || strictlyBetter || (tied && addressPreferred)) {
                challengerScore = score
                challenger = freeByStart.find(Key(representativeStart))
            }
        }
        if (challenger == 0) { return baselineGap }
        let modelLimit = iMax(freeByStart.value(baselineGap) - freeByStart.key(baselineGap).a, freeByStart.value(challenger) - freeByStart.key(challenger).a)
        let freshRisk = lifetimeModel.newRisk(length)
        let baselineScore = causalPrimalLoss(baselineGap, length, highSide, modelLimit, freshRisk)
        let alternativeScore = causalPrimalLoss(challenger, length, highSide, modelLimit, freshRisk)
        return if (alternativeScore + 1e-9 < baselineScore) { challenger } else { baselineGap }
    }

    public func primalGapLoss(gapLength: Int64, length: Int64): Float64 { return primalGapValue[gapLength] - primalGapValue[gapLength - length] }

    public func scoreGap(gapLength: Int64, length: Int64): Int64 {
        let slack = gapLength - length
        var score = slack * recentLengths.size
        if (slack > 0 && slack <= 40) {
            var misses: Int64 = 0
            for (request in slack + 1..=40) { misses += recentFrequency[request] }
            score += kUnfitPenaltyScale * misses
        }
        return score
    }

    public func observationKeyEqual(lhs: Observation, rhs: Observation): Bool {
        if (lhs.kind != rhs.kind) { return false }
        return lhs.kind <= 0 || lhs.value == rhs.value
    }

    public func nextRandom(): Int64 {
        randomState = (randomState ^ (randomState << 13)) & 0xffffffff
        randomState = (randomState ^ (randomState >> 17)) & 0xffffffff
        randomState = (randomState ^ (randomState << 5)) & 0xffffffff
        return randomState
    }

    public func sampleScenario(): Array<Observation> {
        let result = Array<Observation>(kMcDepth, repeat: Observation())
        let n = observedHistory.size
        let minStart = if (n > 128) { n - 128 } else { 0 }
        let starts = ArrayList<Int64>()
        let maxStart = if (n >= kMcDepth) { n - kMcDepth } else { 0 }
        if (n < kMcDepth + 2) { return result }
        var context = iMin(3, n - 1)
        while (context > 0 && starts.size == 0) {
            let contextBegin = n - context
            for (start in minStart + context..=maxStart) {
                var matches = true
                for (offset in 0..context) {
                    if (!observationKeyEqual(observedHistory.get(contextBegin + offset), observedHistory.get(start - context + offset))) { matches = false; break }
                }
                if (matches) { starts.add(start) }
            }
            context--
        }
        if (starts.size == 0) { for (start in minStart..=maxStart) { starts.add(start) } }
        if (starts.size == 0) { return result }
        let start = starts[nextRandom() % starts.size]
        for (offset in 0..kMcDepth) { result[offset] = observedHistory.get(start + offset) }
        return result
    }

    public func makeRolloutState(): RolloutState {
        let state = RolloutState()
        state.confidentRecentAddress = !lifoLaneDisabledForScale && hasLifoDeletionConfidence()
        var it = freeByStart.first()
        while (it != 0) {
            let start = freeByStart.key(it).a
            state.gaps.put(Key(start), SimGap(freeByStart.value(it), gapCohort.value(gapCohort.find(Key(start)))))
            it = freeByStart.next(it)
        }
        state.trenchLength = trenchLength
        state.nextPid = pipes.size
        state.recentLengths = recentLengths.clone()
        state.recentFrequency = recentFrequency.clone()
        state.lengthOccurrenceCount = lengthOccurrenceCount.clone()
        state.removedLengthCohort = Array<Array<Int64>>(41, {i => removedLengthCohort[i].clone()})
        state.parityCohortMode = parityCohortMode
        state.runLeftDisabledBySmoothTrend = runLeftDisabledBySmoothTrend
        state.alternatingDeleteMode = alternatingDeleteMode
        state.predictedDeletedParity = predictedDeletedParity
        state.lastDeletedPid = lastDeletedPid
        state.lastDeletedLength = lastDeletedLength
        state.strideTwoDeleteTransitions = strideTwoDeleteTransitions
        for (pid in 1..pipes.size) {
            let pipe = pipes[pid]
            if (!pipe.active) { continue }
            state.active.add(SimPipe(pid, pipe.start, pipe.length, pipe.sizeCohort))
        }
        return state
    }

    public func topGapCandidates(length: Int64, highSide: Bool, sizeCohort: Int64): ArrayList<GapCandidate> {
        var index = freeBySize
        if (parityCohortMode) {
            let preferred = freeBySizeCohort[sizeCohort]
            if (preferred.lower(Key(length, 0)) != 0) { index = preferred } else { index = freeBySizeShared }
        }
        let candidates = ArrayList<GapCandidate>()
        var it = index.lower(Key(length, 0))
        while (it != 0) {
            let key = index.key(it)
            let slack = key.a - length
            if (slack > 40) { break }
            candidates.add(GapCandidate(key.b, scoreGap(key.a, length)))
            it = index.next(it)
        }
        // Explicit insertion sort uses the exact score/address comparator.
        var i: Int64 = 1
        while (i < candidates.size) {
            let candidate = candidates[i]
            var j = i
            while (j > 0) {
                let previous = candidates[j - 1]
                let less = if (candidate.score != previous.score) { candidate.score < previous.score }
                    else { if (highSide) { candidate.start > previous.start } else { candidate.start < previous.start } }
                if (!less) { break }
                candidates[j] = previous
                j--
            }
            candidates[j] = candidate
            i++
        }
        while (candidates.size > 3) { candidates.remove(at: candidates.size - 1) }
        return candidates
    }

    public func chooseGapWithRollout(length: Int64, highSide: Bool, sizeCohort: Int64, baselineGap: Int64): Int64 {
        if (mcDecisionsUsed >= kMcDecisionBudget || observedHistory.size < 32 || freeByStart.size > kMcMaxGaps || activePipeCount > kMcMaxActivePipes) { return freeByStart.key(baselineGap).a }
        let candidates = topGapCandidates(length, highSide, sizeCohort)
        if (candidates.size < 2 || candidates[0].start != freeByStart.key(baselineGap).a) { return freeByStart.key(baselineGap).a }
        mcDecisionsUsed++
        let base = makeRolloutState()
        randomState = 0x9e3779b9 ^ ((pipes.size * 0x85ebca6b) & 0xffffffff) ^ ((length * 0xc2b2ae35) & 0xffffffff) ^ (trenchLength & 0xffffffff)
        if (randomState == 0) { randomState = 1 }
        let scenarios = Array<Array<Observation>>(kMcTrials, {_ => Array<Observation>(kMcDepth, repeat: Observation())})
        for (trial in 0..kMcTrials) { scenarios[trial] = sampleScenario() }
        let totalTrench = Array<Int64>(3, repeat: 0)
        for (candidate in 0..candidates.size) {
            for (trial in 0..kMcTrials) {
                let simulation = base.deepCopy()
                simulation.placeAtCandidate(candidates[candidate].start, length, highSide)
                for (event in scenarios[trial]) { simulation.apply(event) }
                totalTrench[candidate] += simulation.trenchLength
                mcRolloutsRun++
            }
        }
        var best: Int64 = 0
        for (candidate in 1..candidates.size) { if (totalTrench[candidate] < totalTrench[best]) { best = candidate } }
        if (best != 0 && totalTrench[best] + kMcTrials * kMcMinimumMeanSavingM <= totalTrench[0]) { return candidates[best].start }
        return freeByStart.key(baselineGap).a
    }

    public func hasSteadySizeTrend(): Bool {
        if (recentLengths.size < 128) { return false }
        let distinctLengths = Array<Int64>(3, repeat: 0)
        var distinctCount: Int64 = 0
        var previous: Int64 = -1
        var i = recentLengths.size - 1
        while (i >= 0) {
            let length = recentLengths.get(i)
            i--
            if (length == previous) { continue }
            distinctLengths[distinctCount] = length
            distinctCount++
            previous = length
            if (distinctCount == 3) { break }
        }
        if (distinctCount < 3) { return false }
        return distinctLengths[0] - distinctLengths[1] == distinctLengths[1] - distinctLengths[2]
    }

    public func tailGap(): Int64 {
        if (freeByStart.isEmpty()) { return 0 }
        let it = freeByStart.last()
        return if (freeByStart.value(it) == trenchLength) { it } else { 0 }
    }

    public func bestFittingGapBefore(length: Int64, highSide: Bool, sizeCohort: Int64, endLimit: Int64): Int64 {
        var best: Int64 = 0
        var bestScore: Int64 = Int64.Max
        var it = freeByStart.first()
        while (it != 0) {
            let start = freeByStart.key(it).a
            let end = freeByStart.value(it)
            let next = freeByStart.next(it)
            if (end > endLimit || end - start < length) { it = next; continue }
            if (parityCohortMode) {
                let owner = gapCohort.value(gapCohort.find(Key(start)))
                if (owner >= 0 && owner != sizeCohort) { it = next; continue }
            }
            let score = scoreGap(end - start, length)
            if (score < bestScore || (score == bestScore && best != 0 &&
                (if (highSide) { start > freeByStart.key(best).a } else { start < freeByStart.key(best).a }))) {
                bestScore = score
                best = it
            }
            it = next
        }
        return best
    }

    public func projectedNextClassCapacity(obstacles: ArrayList<Key>, candidateStart: Int64, length: Int64, nextLength: Int64): Int64 {
        if (candidateStart < 0 || nextLength <= 0) { return -1 }
        var low: Int64 = 0
        var high = obstacles.size
        while (low < high) {
            let middle = low + (high - low) / 2
            if (obstacles[middle].a < candidateStart) { low = middle + 1 } else { high = middle }
        }
        let leftEnd = if (low == 0) { 0 } else { obstacles[low - 1].b }
        let rightStart = if (low == obstacles.size) { trenchLength } else { obstacles[low].a }
        if (leftEnd > candidateStart || rightStart < candidateStart + length) { return -1 }
        return (candidateStart - leftEnd) / nextLength + (rightStart - candidateStart - length) / nextLength
    }

    public func chooseCounterfactualCapacityGap(length: Int64, nextLength: Int64, fallbackHighSide: Bool, sizeCohort: Int64, baselineGap: Int64): Array<Int64> {
        let fallbackSide: Int64 = if (fallbackHighSide) { 1 } else { 0 }
        if (activePipeCount > 4096 || freeByStart.size > 4096) { return [0, fallbackSide] }
        let obstacles = ArrayList<Key>()
        // Non-overlapping positive-length pipes have the same start/end order.
        // Iterating activeByEnd directly yields the C++ sorted obstacle vector.
        var obstacleNode = activeByEnd.first()
        while (obstacleNode != 0) {
            let pid = activeByEnd.value(obstacleNode)
            let pipe = pipes[pid]
            if (pipe.active && !(pipe.length == length && (pid & 1) == predictedDeletedParity)) {
                obstacles.add(Key(pipe.start, pipe.start + pipe.length))
            }
            obstacleNode = activeByEnd.next(obstacleNode)
        }
        let baselineStart = if (baselineGap == 0) { -1 }
            else { if (fallbackHighSide) { freeByStart.value(baselineGap) - length } else { freeByStart.key(baselineGap).a } }
        let baselineCapacity = projectedNextClassCapacity(obstacles, baselineStart, length, nextLength)
        var best: Int64 = 0
        var bestHighSide = fallbackHighSide
        var bestStart: Int64 = -1
        var bestCapacity: Int64 = -1
        var bestBaseScore: Int64 = Int64.Max
        let tail = tailGap()
        let firstMode: Int64 = if (parityCohortMode) { 1 } else { 0 }
        let lastMode: Int64 = if (parityCohortMode) { 2 } else { 0 }
        for (ownerMode in firstMode..=lastMode) {
            if (ownerMode == 2 && best != 0) { break }
            var it = freeByStart.first()
            while (it != 0) {
                let gapStart = freeByStart.key(it).a
                let gapEnd = freeByStart.value(it)
                let gapLength = gapEnd - gapStart
                let owner = gapCohort.value(gapCohort.find(Key(gapStart)))
                let next = freeByStart.next(it)
                if (gapLength < length || (tail != 0 && it == tail) ||
                    (ownerMode == 1 && owner != sizeCohort) || (ownerMode == 2 && owner >= 0)) { it = next; continue }
                let baseScore = scoreGap(gapLength, length)
                for (side in 0..2) {
                    let high = side != 0
                    let candidateStart = if (high) { gapEnd - length } else { gapStart }
                    let capacity = projectedNextClassCapacity(obstacles, candidateStart, length, nextLength)
                    if (capacity < 0) { continue }
                    let tieSidePreferred = high == fallbackHighSide
                    let bestTieSidePreferred = bestHighSide == fallbackHighSide
                    let addressPreferred = best != 0 && (if (high) { candidateStart > bestStart } else { candidateStart < bestStart })
                    if (capacity > bestCapacity || (capacity == bestCapacity && baseScore < bestBaseScore) ||
                        (capacity == bestCapacity && baseScore == bestBaseScore && tieSidePreferred && !bestTieSidePreferred) ||
                        (capacity == bestCapacity && baseScore == bestBaseScore && tieSidePreferred == bestTieSidePreferred && addressPreferred)) {
                        best = it
                        bestHighSide = high
                        bestStart = candidateStart
                        bestCapacity = capacity
                        bestBaseScore = baseScore
                    }
                }
                it = next
            }
        }
        if (best == 0 || bestCapacity <= baselineCapacity) { return [0, fallbackSide] }
        return [best, if (bestHighSide) { 1 } else { 0 }]
    }

    public func bestFittingGap(length: Int64, highSide: Bool, sizeCohort: Int64): Int64 {
        if (parityCohortMode) {
            let preferred = bestFittingGapFromSet(freeBySizeCohort[sizeCohort], length, highSide)
            if (preferred != 0) { return preferred }
            let shared = bestFittingGapFromSet(freeBySizeShared, length, highSide)
            if (shared != 0) { return shared }
            return 0
        }
        return bestFittingGapFromSet(freeBySize, length, highSide)
    }

    public func bestFittingGapFromSet(gaps: OrderedMap<Int64>, length: Int64, highSide: Bool): Int64 {
        let recycleRecent = !parityCohortMode && activePipeCount > kMcMaxActivePipes && hasLifoDeletionConfidence()
        let confidentRecentAddress = highSide && !lifoLaneDisabledForScale && hasLifoDeletionConfidence()
        let it = gaps.lower(Key(length, 0))
        if (it == 0) { return 0 }
        if (recentLengths.size == 0) { return freeByStart.find(Key(gaps.key(it).b)) }
        let candidates = ArrayList<Key>()
        var candidate = it
        while (candidate != 0) {
            if (confidentRecentAddress) { candidate = gaps.prev(gaps.upper(Key(gaps.key(candidate).a, Int64.Max))) }
            let gapLength = gaps.key(candidate).a
            var representativeStart = gaps.key(candidate).b
            if (recycleRecent) {
                let age = freeBySizeAge.prev(freeBySizeAge.upper(Key(gapLength, Int64.Max, Int64.Max)))
                representativeStart = freeBySizeAge.key(age).c
            }
            candidates.add(Key(gapLength, representativeStart))
            if (gapLength - length > 40) { break }
            candidate = gaps.upper(Key(gapLength, Int64.Max))
        }
        let historySize = recentLengths.size
        var bestScore = Int64.Max
        var legacyBest: Int64 = 0
        for (candidateKey in candidates) {
            let gapLength = candidateKey.a
            let representativeStart = candidateKey.b
            let slack = gapLength - length
            var score = slack * historySize
            if (slack > 0 && slack <= 40) {
                var misses: Int64 = 0
                for (request in slack + 1..=40) { misses += recentFrequency[request] }
                score += kUnfitPenaltyScale * misses
            }
            if (score < bestScore || (score == bestScore && legacyBest != 0 &&
                (if (highSide) { representativeStart > freeByStart.key(legacyBest).a } else { representativeStart < freeByStart.key(legacyBest).a }))) {
                bestScore = score
                legacyBest = freeByStart.find(Key(representativeStart))
            }
        }
        var best = legacyBest
        let ordinaryLargeMode = !parityCohortMode && (activePipeCount > kMcMaxActivePipes ||
            (activePipeCount >= 128 && primalStep >= 256 && primalRecentDeletes >= 32))
        if (ordinaryLargeMode && candidates[0].a > length) {
            let maxCandidateGap = candidates[candidates.size - 1].a
            if (maxCandidateGap > kPrimalGapValueCap) { primalCapFallbacks++ }
            else if (ensurePrimalGapValues(maxCandidateGap)) {
                var primalBestScore = primalGapLoss(freeByStart.value(legacyBest) - freeByStart.key(legacyBest).a, length)
                var primalBest = legacyBest
                for (candidateKey in candidates) {
                    let score = primalGapLoss(candidateKey.a, length)
                    if (score + 1e-9 < primalBestScore) {
                        primalBestScore = score
                        primalBest = freeByStart.find(Key(candidateKey.b))
                    }
                }
                if (primalBest != 0) {
                    primalBest = chooseCausalLifetimeGap(candidates, length, highSide, primalBest)
                    primalScoredDecisions++
                    if (primalFirstActivationEvent == 0) { primalFirstActivationEvent = primalStep + 1 }
                    if (primalBest != legacyBest) { primalChangedSelections++ }
                    best = primalBest
                }
            }
        }
        if (recycleRecent && best != 0) {
            let first = gaps.lower(Key(freeByStart.value(best) - freeByStart.key(best).a, 0))
            if (gaps.key(first).b != freeByStart.key(best).a) { recencyDifferentSelections++ }
        }
        return best
    }

    public func hasSameLengthRecentRun(length: Int64): Bool {
        if (recentLengths.size < kSameLengthRightRun) { return false }
        for (seen in 0..kSameLengthRightRun) { if (recentLengths.get(recentLengths.size - 1 - seen) != length) { return false } }
        return true
    }

    public func hasSmoothSizeTrendWith(currentLength: Int64): Bool {
        if (recentLengths.size == 0) { return false }
        let currentRunAlreadyInHistory = recentLengths.back() == currentLength
        let priorRunLengths = Array<Int64>(2, repeat: 0)
        var distinctCount: Int64 = 0
        var firstRun = true
        var lastRunLength: Int64 = -1
        var i = recentLengths.size - 1
        while (i >= 0) {
            let length = recentLengths.get(i)
            i--
            if (firstRun) {
                firstRun = false
                lastRunLength = length
                if (!currentRunAlreadyInHistory) { priorRunLengths[distinctCount] = length; distinctCount++ }
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

    public func consumeAtSide(it: Int64, length: Int64, highSide: Bool): Int64 {
        let start = freeByStart.key(it).a
        let end = freeByStart.value(it)
        let cohort = gapCohort.value(gapCohort.find(Key(start)))
        let freedAt = gapFreedAt.value(gapFreedAt.find(Key(start)))
        let placementStart = if (highSide) { end - length } else { start }
        eraseGap(it)
        if (start < placementStart) { addFreeGap(start, placementStart, cohort, freedAt) }
        let placementEnd = placementStart + length
        if (placementEnd < end) { addFreeGap(placementEnd, end, cohort, freedAt) }
        return placementStart
    }

    public func recordLength(length: Int64): Unit {
        recentLengths.pushBack(length)
        recentFrequency[length]++
        if (recentLengths.size > kHistoryWindow) { recentFrequency[recentLengths.get(0)]--; recentLengths.popFront() }
    }

    public func eraseGap(it: Int64): Unit {
        let start = freeByStart.key(it).a
        let end = freeByStart.value(it)
        let gapLength = end - start
        let cohort = gapCohort.value(gapCohort.find(Key(start)))
        let bucket = iMin(kPrimalGapValueCap + 1, gapLength)
        primalGapCounts[bucket]--
        freeBySizeAge.eraseKey(Key(gapLength, gapFreedAt.value(gapFreedAt.find(Key(start))), start))
        gapFreedAt.eraseKey(Key(start))
        freeBySize.eraseKey(Key(gapLength, start))
        if (cohort >= 0 && cohort <= 1) { freeBySizeCohort[cohort].eraseKey(Key(gapLength, start)) }
        else { freeBySizeShared.eraseKey(Key(gapLength, start)) }
        gapCohort.eraseKey(Key(start))
        freeByStart.eraseNode(it)
    }

    public func addFreeGap(start: Int64, end: Int64, cohort: Int64): Unit { addFreeGap(start, end, cohort, 0) }
    public func addFreeGap(start: Int64, end: Int64, cohort: Int64, freedAt: Int64): Unit {
        var mergedStart = start
        var mergedEnd = end
        var mergedCohort = cohort
        var mergedFreedAt = freedAt
        if (mergedStart >= mergedEnd) { return }
        var it = freeByStart.lower(Key(mergedStart))
        if (it != freeByStart.first()) {
            let previous = freeByStart.prev(it)
            if (freeByStart.value(previous) >= mergedStart) {
                let previousStart = freeByStart.key(previous).a
                if (gapCohort.value(gapCohort.find(Key(previousStart))) != mergedCohort) { mergedCohort = -1 }
                mergedFreedAt = iMax(mergedFreedAt, gapFreedAt.value(gapFreedAt.find(Key(previousStart))))
                mergedStart = previousStart
                mergedEnd = iMax(mergedEnd, freeByStart.value(previous))
                eraseGap(previous)
                it = freeByStart.lower(Key(mergedStart))
            }
        }
        while (it != 0 && freeByStart.key(it).a <= mergedEnd) {
            let itStart = freeByStart.key(it).a
            if (gapCohort.value(gapCohort.find(Key(itStart))) != mergedCohort) { mergedCohort = -1 }
            mergedFreedAt = iMax(mergedFreedAt, gapFreedAt.value(gapFreedAt.find(Key(itStart))))
            mergedEnd = iMax(mergedEnd, freeByStart.value(it))
            let next = freeByStart.next(it)
            eraseGap(it)
            it = next
        }
        freeByStart.put(Key(mergedStart), mergedEnd)
        let gapLength = mergedEnd - mergedStart
        primalGapCounts[iMin(kPrimalGapValueCap + 1, gapLength)]++
        freeBySize.put(Key(gapLength, mergedStart), 0)
        freeBySizeAge.put(Key(gapLength, mergedFreedAt, mergedStart), 0)
        gapFreedAt.put(Key(mergedStart), mergedFreedAt)
        gapCohort.put(Key(mergedStart), mergedCohort)
        if (mergedCohort >= 0 && mergedCohort <= 1) { freeBySizeCohort[mergedCohort].put(Key(gapLength, mergedStart), 0) }
        else { freeBySizeShared.put(Key(gapLength, mergedStart), 0) }
    }

    public func printPlacement(digs: Int64, start: Int64): Unit { if (emit) { answer(digs, start) } }
    public func printInvalidPidFallback(): Unit { if (emit) { answerRemoval(0) } }
}
