"""Transfer only trial42's censored birth-context model into frozen trial22."""
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARENT = ROOT / 'releases/988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4/solution.cpp'
DONOR = ROOT / 'proposals/trial_0042/candidate_0.cpp'
assert hashlib.sha256(PARENT.read_bytes()).hexdigest() == '988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4'
assert hashlib.sha256(DONOR.read_bytes()).hexdigest() == 'b25231a837c1d7f38c56d3b6d8c885f1cfa612e3f946963837977dbc6b970d8c'
text = PARENT.read_text()
donor = DONOR.read_text()
model = donor.split('class CensoredLifetimeModel {', 1)[1].split('\nclass Allocator {', 1)[0]
model = 'class CensoredLifetimeModel {' + model
model = re.sub(r'\bU\b', 'std::uint64_t', model)
model = re.sub(r'\bkHistory\b', 'kHistoryWindow', model)
begin = text.index('class CensoredLifetimeModel {')
end = text.index('class Allocator {', begin)
text = text[:begin] + model + '\n' + text[end:]

def replace(old, new):
    global text
    assert text.count(old) == 1, old[:120]
    text = text.replace(old, new, 1)

replace('    CensoredLifetimeModel lifetimeModel;\n', '''    CensoredLifetimeModel lifetimeModel;
    bool birthContextPreviousWasDeletion = false;
    std::uint64_t birthContextCompared = 0;
    std::uint64_t birthContextChanged = 0;
''')
replace('    void place(int length) {\n        lifetimeModel.advance();\n', '''    void place(int length) {
        lifetimeModel.advance();
        lifetimeModel.setBirthContext(birthContextPreviousWasDeletion);
        birthContextPreviousWasDeletion = false;
''')
replace('        lifetimeModel.observeDeletion(index);\n', '''        lifetimeModel.observeDeletion(index);
        birthContextPreviousWasDeletion = true;
''')
replace('                           int modelLimit, double freshRisk) {\n',
        '                           int modelLimit, double freshRisk, bool useContext) {\n')
replace('lifetimeModel.existingRisk(left->second);',
        'lifetimeModel.existingRisk(left->second, useContext);')
replace('lifetimeModel.existingRisk(right->second);',
        'lifetimeModel.existingRisk(right->second, useContext);')
replace('''        const double freshRisk = lifetimeModel.newRisk(length);
        const double baselineScore = causalPrimalLoss(
            baselineGap, length, highSide, modelLimit, freshRisk);
        const double alternativeScore = causalPrimalLoss(
            challenger, length, highSide, modelLimit, freshRisk);
        return alternativeScore + 1e-9 < baselineScore ? challenger : baselineGap;
''', '''        const double pooledFresh = lifetimeModel.newRisk(length, false);
        const double contextFresh = lifetimeModel.newRisk(length, true);
        const double pooledBaseline = causalPrimalLoss(
            baselineGap, length, highSide, modelLimit, pooledFresh, false);
        const double pooledAlternative = causalPrimalLoss(
            challenger, length, highSide, modelLimit, pooledFresh, false);
        const double contextBaseline = causalPrimalLoss(
            baselineGap, length, highSide, modelLimit, contextFresh, true);
        const double contextAlternative = causalPrimalLoss(
            challenger, length, highSide, modelLimit, contextFresh, true);
        const bool pooledSwitch = pooledAlternative + 1e-9 < pooledBaseline;
        const bool contextSwitch = contextAlternative + 1e-9 < contextBaseline;
        ++birthContextCompared;
        if (pooledSwitch != contextSwitch) ++birthContextChanged;
        return contextSwitch ? challenger : baselineGap;
''')
replace('''            std::cerr << "recency_different_selections="
''', '''            std::cerr << "birth_context_supported_queries="
                      << allocator.lifetimeModel.supportedQueries()
                      << " context_compared_decisions=" << allocator.birthContextCompared
                      << " context_changed_selections=" << allocator.birthContextChanged << '\\n';
            std::cerr << "recency_different_selections="
''')
destination = Path(__file__).with_name('solution.cpp')
assert not destination.exists(), 'Do not overwrite a registered candidate'
destination.write_text(text)
print(hashlib.sha256(destination.read_bytes()).hexdigest())
