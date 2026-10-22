package pipes

import std.collection.*

func checkModel(condition: Bool, name: String): Int64 {
    if (condition) { return 0 }
    println("FAIL: ${name}")
    return 1
}

main(): Int64 {
    var failed: Int64 = 0
    let original = RolloutState()
    original.confidentRecentAddress = true
    original.trenchLength = 120
    original.nextPid = 4
    original.gaps.put(Key(10), SimGap(30, 1))
    original.gaps.put(Key(40), SimGap(60, -1))
    original.active.add(SimPipe(1, 0, 10, 0))
    original.active.add(SimPipe(2, 30, 10, 1))
    original.active.add(SimPipe(3, 60, 20, 0))
    original.recentLengths.pushBack(10)
    original.recentLengths.pushBack(20)
    original.recentFrequency[10] = 1
    original.recentFrequency[20] = 1
    original.lengthOccurrenceCount[10] = 2
    original.removedLengthCohort[10][0] = 3
    original.removedLengthCohort[10][1] = 4
    original.parityCohortMode = true
    original.runLeftDisabledBySmoothTrend = true
    original.alternatingDeleteMode = true
    original.predictedDeletedParity = 0
    original.lastDeletedPid = 14
    original.lastDeletedLength = 10
    original.strideTwoDeleteTransitions = 7
    let copy = original.deepCopy()
    failed += checkModel(copy.confidentRecentAddress && copy.trenchLength == 120 &&
        copy.nextPid == 4 && copy.parityCohortMode && copy.runLeftDisabledBySmoothTrend &&
        copy.alternatingDeleteMode && copy.predictedDeletedParity == 0 &&
        copy.lastDeletedPid == 14 && copy.lastDeletedLength == 10 &&
        copy.strideTwoDeleteTransitions == 7, "deepCopy scalar fields")
    copy.gaps.eraseKey(Key(10))
    copy.gaps.put(Key(90), SimGap(100, 0))
    copy.active.remove(at: 1)
    var modifiedPipe = copy.active[0]
    modifiedPipe.start = 99
    copy.active[0] = modifiedPipe
    copy.recentLengths.popFront()
    copy.recentLengths.pushBack(30)
    copy.recentFrequency[10] = 99
    copy.lengthOccurrenceCount[10] = 99
    copy.removedLengthCohort[10][0] = 99
    copy.removedLengthCohort[10][1] = 99
    copy.removedLengthCohort[11][0] = 77
    failed += checkModel(original.gaps.size == 2 && original.gaps.find(Key(10)) != 0 &&
        original.gaps.find(Key(90)) == 0, "deepCopy ordered gaps")
    failed += checkModel(original.active.size == 3 && original.active[0].start == 0 &&
        original.active[1].pid == 2 && copy.active.size == 2 && copy.active[1].pid == 3,
        "struct copies and ArrayList erase shifts")
    failed += checkModel(original.recentLengths.size == 2 && original.recentLengths.get(0) == 10 &&
        original.recentLengths.get(1) == 20 && copy.recentLengths.get(0) == 20 &&
        copy.recentLengths.get(1) == 30, "deepCopy ring")
    failed += checkModel(original.recentFrequency[10] == 1 && original.lengthOccurrenceCount[10] == 2 &&
        original.removedLengthCohort[10][0] == 3 && original.removedLengthCohort[10][1] == 4 &&
        original.removedLengthCohort[11][0] == 0 && copy.removedLengthCohort[11][1] == 0,
        "deepCopy independent nested arrays")

    let swapPop = ArrayList<SimPipe>([SimPipe(1, 1, 1, 0), SimPipe(2, 2, 2, 1), SimPipe(3, 3, 3, 0)])
    let removedPipe = swapPop[1]
    swapPop[1] = swapPop[swapPop.size - 1]
    swapPop.remove(at: swapPop.size - 1)
    failed += checkModel(removedPipe.pid == 2 && swapPop.size == 2 && swapPop[0].pid == 1 &&
        swapPop[1].pid == 3, "ArrayList swap-pop value semantics")

    let trend = Ring<Int64>(0)
    for (_ in 0..46) { trend.pushBack(2) }
    for (_ in 0..46) { trend.pushBack(4) }
    for (_ in 0..45) { trend.pushBack(8) }
    failed += checkModel(predictNextGeometricSize(trend, 8) == 0, "geometric run45")
    trend.pushBack(8)
    failed += checkModel(predictNextGeometricSize(trend, 8) == 16, "geometric run46")
    failed += checkModel(trendAlignedHighSide(trend, 8, 1, 40, true) &&
        !trendAlignedHighSide(trend, 8, 9, 40, false), "geometric alignment")

    let merging = RolloutState()
    merging.addFreeGap(10, 20, 0)
    merging.addFreeGap(30, 40, 0)
    merging.addFreeGap(20, 30, 1)
    failed += checkModel(merging.gaps.size == 1 && merging.gaps.key(merging.gaps.first()).a == 10 &&
        merging.gaps.value(merging.gaps.first()).end == 40 &&
        merging.gaps.value(merging.gaps.first()).cohort == -1, "merge both sides mixed cohort")
    merging.splitGap(10, 7, true)
    failed += checkModel(merging.gaps.size == 1 && merging.gaps.value(merging.gaps.first()).end == 33,
        "split high side")

    let tie = RolloutState()
    tie.gaps.put(Key(0), SimGap(10, -1))
    tie.gaps.put(Key(20), SimGap(30, -1))
    if (let Some(start) <- tie.bestGap(5, true, 0)) {
        failed += checkModel(start == 0, "equal lengths keep first eligible")
    } else { failed++ }
    tie.confidentRecentAddress = true
    if (let Some(start) <- tie.bestGap(5, true, 0)) {
        failed += checkModel(start == 20, "confident high-side equal-length exception")
    } else { failed++ }
    tie.recordLength(1)
    for (_ in 0..2048) { tie.recordLength(40) }
    failed += checkModel(tie.recentLengths.size == 2048 && tie.recentFrequency[1] == 0 &&
        tie.recentFrequency[40] == 2048, "history eviction2048")

    if (failed == 0) { println("models: all checks passed") }
    return failed
}
