# Slop Audit card copy

Edit the text under any `## key` heading to change what the page says. Words in
{braces} are fill-ins the code supplies (a number, a slug); leave them in place.
Each section is one paragraph; wrap the lines however you like, the app collapses
them to a single string. Changes take effect on the next app start.

## question
How many end-to-end test cases would fully cover this code?

## verdict.finite
Can be fully verified.

## verdict.infinite
Can't be fully verified.

## label.practical
test cases can walk every branch the code can reach. This is the list you actually work through.

## unit.infinite
unbounded (no finite number exists)

# --- The green (finite) explanation -----------------------------------------

## detail.finite
Full verification is possible here because no function shares mutable state. This means that we can count every possible state change. The Slop Audit builds the graph of every branch the code can reach and finds the fewest paths that walk all of it. {cover} test cases cover every path, both the taken and the not-taken side of each decision. There is no need to test every theoretically possible combination of functions because we can determine which ones call which other ones.

# --- The red (infinite) explanation -----------------------------------------

## detail.infinite
{mutable} of {total} {plural} read shared mutable state that can grow without limit. Every value that state can take is another situation the function has to be tested in, and nothing caps how many there are, so no finite set of tests reaches all of them. More tests will not close that gap. Taking the shared state out of those {plural} will: once a function reads only its inputs, the situations become finite and you can cover them.

## status.infinite.Healthy
A few functions stand between this code and full coverage.

## status.infinite.Not Healthy
A large share of the code is tangled in shared state, until that is undone that part of the code cannot be exhaustively tested.

## status.infinite.Slop
This code cannot be exhaustively tested.

## detail.na
Point it at a public repository with source in a language the analyzer reads (Python, TypeScript, JavaScript, Java, Go, Rust).

# --- Share text -------------------------------------------------------------

## share.infinite
{slug}: fully covering it end to end would literally take an infinite number of tests. {mutable} of {total} functions read shared state that can be changed at any time from anywhere in the code. 100% coverage can still be achieved even if we test only one of these possibilities.

## share.finite
{slug} passes the Slop Audit: nothing shares mutable state, so every function can be checked on its own and exhaustive testing is possible. slopaudit.org

## share.na
I ran {slug} through the Slop Audit. slopaudit.org

# --- The two metric groups --------------------------------------------------

## group.core.title
Can this code be verified?

## group.core.note
The finite-testability indicators. These have no compliance-framework mapping on purpose: they are the ceiling on what every other control below can ever prove.

## group.audit.title
How it maps to your audit

## group.audit.note
Each signal below is cross-indexed to the Slop Audit's enterprise dimensions and the compliance controls they answer to.

## footer.fine
A full Slop Audit scores all 18 enterprise compliance dimensions and produces SOC 2 evidence as a byproduct. This page runs the static Layer 1 indicators only. It never executes the repo's code.

# --- Metric names and plain-language meanings -------------------------------

## label.L1.18
How much depends on hidden state

## tech.L1.18
L1.18 · mutable-state ratio

## meaning.L1.18
The share of functions whose behavior depends on state outside their inputs. Each one pulls in shared state that can be changed by another part of the code at any time, which is why this code can never be exhaustively tested. It is also the single number that predicts race conditions, order-dependent test failures, and stale-cache bugs.

## label.L1.19
Decisions that could be exhaustively checked

## tech.L1.19
L1.19 · decision-space coverage

## meaning.L1.19
How many finitely-enumerable decisions (dispatch keys, match arms, enum branches) exist in the code. What fraction your tests actually cover is the real L1.19 number, and it requires running your test suite, which this tool never does. Run the [CLI](https://github.com/openhonest/slop-audit) on your machines to get the coverage figure.

## label.L1.15
Escapes from the type system

## tech.L1.15
L1.15 · type-escape density

## meaning.L1.15
How often the code opts out of its own type checker (any, # type: ignore, interface{}, dynamic) per thousand lines. Each escape is a spot the compiler can no longer protect, so a test has to cover it by hand.

## label.L1.17
“God-files”, files too big to hold in your head

## tech.L1.17
L1.17 · god-file concentration

## meaning.L1.17
The share of files over 1,000 lines, an AI smell. AI assistants pile new code into the biggest file they can find; without a reviewer forcing a split, these grow until every change touches them and merge conflicts multiply.

## label.L1.16
Indications that a human ever edited the file

## tech.L1.16
L1.16 · trailing-whitespace density

## meaning.L1.16
Harmless on its own, but an AI smell: lines left with trailing whitespace mean no editor or formatter touched the file between 'the AI wrote it' and 'it landed on main', which usually means no human reviewed it either.

## label.L1.10
Automated build-and-test pipelines

## tech.L1.10
L1.10 · CI/CD pipelines

## meaning.L1.10
How many pipelines build, test, and gate each change before it ships. Zero means every merge is a manual act of faith.

## label.L1.11
A reproducible environment

## tech.L1.11
L1.11 · containerization

## meaning.L1.11
Whether the repo ships a container or orchestration config so it runs the same on every machine. The container is the constraint that keeps an AI's environment-coupling habits from becoming the classic 'it works on *my* machine.'

## label.L1.9
Checks that run before every commit

## tech.L1.9
L1.9 · pre-commit hooks

## meaning.L1.9
Whether automated checks run before code can even be committed, the first gate that catches AI output before a human ever sees it.

# --- Landing page -----------------------------------------------------------

## hero.kicker
The Slop Audit · an open standard

## hero.title
How many test cases would it take to exhaustively test your code?

## hero.sub
Paste a public GitHub repo in one of 7 supported languages and find out. For code that allows shared mutable state, the stuff AI writes by the truckload, the answer is often <strong>infinitely many</strong>: no finite test suite can ever cover it. The Slop Audit shows you why, function by function, and cross-indexes it to the compliance dimensions your reviewers already track. Nothing is installed. We never run your code.

## example.note
Here's a real audit of our own code. Paste any public repo above to run your own.

## try.text
run the example on

## explain.title
What you're looking at

## explain.body
The headline number is the <strong>mutable-state ratio</strong>: the share of functions whose behavior depends on state they don't own. That state is what makes exhaustive testing impossible no matter how many tests you write, so it's the ceiling on everything else an audit can prove. Below it, each signal is cross-indexed to the enterprise audit dimensions and the compliance controls (SOC 2, NIST, OWASP, ISO) your reviewers already answer to.
