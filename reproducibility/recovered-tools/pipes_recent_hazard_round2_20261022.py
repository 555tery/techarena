"""One pure recent-hazard hypothesis, H=4096 commands, snapshot period=64.

Raw cells, birth sums, active counts, record lifetimes and censoring stay intact.
The Cangjie parent lazily flushes age-bin crossings: snapshots call its existing
flushCrossings before reading those cells, which is logically the same raw state.
For elapsed dt>0, a=exp(-dt/4096), q=(1-a)/(dt/4096), weighted=a*old+q*rawDelta.
Each interval's exposure and deaths are treated as uniformly distributed. This
is a bounded-bucket approximation, not an exact exponential event-time sum.
Bootstrap is clock0/raw0/weighted0; snapshots run at most64 commands apart,
and every fit flushes its remaining interval before using weighted statistics.

The prior8, sqrt(weightedDeaths+prior) error heuristic, pooled error, 2-error
abstention and clamp[0.5,2] remain. That confidence is not claimed calibrated.
No early-lifetime/side changes, parameter options, builds or solver execution.
"""

def _replace(source,old,new):
 assert source.count(old)==1,(old[:120],source.count(old))
 return source.replace(old,new)

_CPP_UPDATE='''    void snapshotRecentHazard() {
        const auto elapsed = clock_ - recentClock_;
        if (elapsed == 0) return;
        const double scaled = static_cast<double>(elapsed) / 4096.0;
        const double decay = std::exp(-scaled);
        const double intervalWeight = (1.0 - decay) / scaled;
        for (std::size_t bin = 0; bin < kBins; ++bin) {
            for (std::size_t length = 1; length <= 40; ++length) {
                const auto& raw = cells_[length][bin];
                auto& recent = recentCells_[length][bin];
                const auto rawExposure = exposure(raw, bin);
                const auto rawDeaths = raw.deaths;
                if (rawExposure < recent.previousExposure || rawDeaths < recent.previousDeaths) {
                    throw std::runtime_error("nonmonotone lifetime raw statistics");
                }
                const double deltaExposure = static_cast<double>(rawExposure - recent.previousExposure);
                const double deltaDeaths = static_cast<double>(rawDeaths - recent.previousDeaths);
                const double oldExposureContribution = decay * recent.weightedExposure;
                const double deltaExposureContribution = intervalWeight * deltaExposure;
                const double oldDeathsContribution = decay * recent.weightedDeaths;
                const double deltaDeathsContribution = intervalWeight * deltaDeaths;
                recent.weightedExposure = oldExposureContribution + deltaExposureContribution;
                recent.weightedDeaths = oldDeathsContribution + deltaDeathsContribution;
                recent.previousExposure = rawExposure;
                recent.previousDeaths = rawDeaths;
            }
        }
        recentClock_ = clock_;
    }

'''

_CJ_UPDATE='''    @OverflowWrapping
    private func snapshotRecentHazard(): Unit {
        let elapsed = clock - recentClock
        if (elapsed <= 0) { return }
        let scaled = Float64(elapsed) / 4096.0
        let decay = exp(-scaled)
        let intervalWeight = (1.0 - decay) / scaled
        let cellData = cells.borrowData()
        let previous = recentRaw.borrowData()
        let weighted = recentWeighted.borrowData()
        let limits = lower.borrowData()
        unsafe {
            for (bin in 0..8) {
                let fitBinLower = limits.read(bin)
                for (length in 1..41) {
                    let index = (length * 8 + bin) * 4
                    let recentIndex = (length * 8 + bin) * 2
                    let active = cellData.read(index + 2)
                    let outstanding: Int64 = if (active == 0) { 0 } else { active * (clock - fitBinLower) - cellData.read(index + 1) }
                    let rawExposure = cellData.read(index) + outstanding
                    let rawDeaths = cellData.read(index + 3)
                    if (rawExposure < previous.read(recentIndex) || rawDeaths < previous.read(recentIndex + 1)) {
                        throw IllegalStateException("nonmonotone lifetime raw statistics")
                    }
                    let deltaExposure = Float64(rawExposure - previous.read(recentIndex))
                    let deltaDeaths = Float64(rawDeaths - previous.read(recentIndex + 1))
                    let oldExposureContribution = decay * weighted.read(recentIndex)
                    let deltaExposureContribution = intervalWeight * deltaExposure
                    let oldDeathsContribution = decay * weighted.read(recentIndex + 1)
                    let deltaDeathsContribution = intervalWeight * deltaDeaths
                    weighted.write(recentIndex, oldExposureContribution + deltaExposureContribution)
                    weighted.write(recentIndex + 1, oldDeathsContribution + deltaDeathsContribution)
                    previous.write(recentIndex, rawExposure)
                    previous.write(recentIndex + 1, rawDeaths)
                }
            }
        }
        recentClock = clock
        blackBox(this)
    }

'''

def apply_cpp(source):
 source=_replace(source,'''    std::array<std::array<Cell, kBins>, 41> cells_{};
    std::array<std::array<Estimate, kBins>, 41> rates_{};''',
 '''    std::array<std::array<Cell, kBins>, 41> cells_{};
    struct RecentCell {
        std::uint64_t previousExposure = 0;
        std::uint64_t previousDeaths = 0;
        double weightedExposure = 0.0;
        double weightedDeaths = 0.0;
    };
    std::array<std::array<RecentCell, kBins>, 41> recentCells_{};
    std::uint64_t recentClock_ = 0;
    std::array<std::array<Estimate, kBins>, 41> rates_{};''')
 source=_replace(source,'    Estimate predict(int length, std::uint64_t age) const {',
 _CPP_UPDATE+'    Estimate predict(int length, std::uint64_t age) const {')
 source=_replace(source,'''                enter(record, bin);
            }
        }
    }

    void observeBirth(int length)''',
 '''                enter(record, bin);
            }
        }
        if (clock_ - recentClock_ >= 64) snapshotRecentHazard();
    }

    void observeBirth(int length)''')
 source=_replace(source,'''    bool fit(double priorHazard) {
        fitted_ = false;''',
 '''    bool fit(double priorHazard) {
        snapshotRecentHazard();
        fitted_ = false;''')
 source=_replace(source,'''                pooledExposure += static_cast<double>(exposure(cells_[length][bin], bin));
                pooledDeaths += static_cast<double>(cells_[length][bin].deaths);''',
 '''                pooledExposure += recentCells_[length][bin].weightedExposure;
                pooledDeaths += recentCells_[length][bin].weightedDeaths;''')
 source=_replace(source,'''                const auto& cell = cells_[length][bin];
                const double borrowedExposure = priorEvents / pooledRate;
                const double denominator = static_cast<double>(exposure(cell, bin)) +
                    borrowedExposure;
                const double shape = static_cast<double>(cell.deaths) + priorEvents;''',
 '''                const auto& recent = recentCells_[length][bin];
                const double borrowedExposure = priorEvents / pooledRate;
                const double denominator = recent.weightedExposure +
                    borrowedExposure;
                const double shape = recent.weightedDeaths + priorEvents;''')
 return source


def apply_cj(source):
 source=_replace(source,'''    private let cells = FastIntBuffer(1312)
    private let rates = FastFloatBuffer(656)''',
 '''    private let cells = FastIntBuffer(1312)
    private let recentRaw = FastIntBuffer(656)
    private let recentWeighted = FastFloatBuffer(656)
    private var recentClock: Int64 = 0
    private let rates = FastFloatBuffer(656)''')
 source=_replace(source,'''    @OverflowWrapping
    public func advance(): Unit { clock++ }''',
 '''    @OverflowWrapping
    public func advance(): Unit {
        clock++
        if (clock - recentClock >= 64) {
            flushCrossings()
            snapshotRecentHazard()
        }
    }''')
 source=_replace(source,'''    @OverflowWrapping
    public func fit(priorHazard: Float64): Bool {''',
 _CJ_UPDATE+'''    @OverflowWrapping
    public func fit(priorHazard: Float64): Bool {''')
 source=_replace(source,'''        flushCrossings()
        fitted = false''',
 '''        flushCrossings()
        snapshotRecentHazard()
        fitted = false''')
 source=_replace(source,'''        let priorEvents: Float64 = 8.0
        let cellData = cells.borrowData()
        let rateData = rates.borrowData()''',
 '''        let priorEvents: Float64 = 8.0
        let cellData = cells.borrowData()
        let weighted = recentWeighted.borrowData()
        let rateData = rates.borrowData()''')
 source=_replace(source,'''                    let index = (length * 8 + bin) * 4
                    let active = cellData.read(index + 2)
                    let fitOutstanding: Int64 = if (active == 0) { 0 } else { active * (clock - fitBinLower) - cellData.read(index + 1) }
                    let fitExposure = cellData.read(index) + fitOutstanding
                    pooledExposure += Float64(fitExposure)
                    pooledDeaths += Float64(cellData.read(index + 3))''',
 '''                    let recentIndex = (length * 8 + bin) * 2
                    pooledExposure += weighted.read(recentIndex)
                    pooledDeaths += weighted.read(recentIndex + 1)''')
 source=_replace(source,'''                    let index = (length * 8 + bin) * 4
                    let active = cellData.read(index + 2)
                    let fitOutstanding: Int64 = if (active == 0) { 0 } else { active * (clock - fitBinLower) - cellData.read(index + 1) }
                    let fitExposure = cellData.read(index) + fitOutstanding
                    let denominator = Float64(fitExposure) + borrowedExposure
                    let shape = Float64(cellData.read(index + 3)) + priorEvents''',
 '''                    let recentIndex = (length * 8 + bin) * 2
                    let denominator = weighted.read(recentIndex) + borrowedExposure
                    let shape = weighted.read(recentIndex + 1) + priorEvents''')
 return source
