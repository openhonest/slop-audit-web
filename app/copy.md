# Slop Audit card copy

Edit the text under any `## key` heading to change what the page says. Words in
{braces} are fill-ins the code supplies (a number, a slug); leave them in place.
Each section is one paragraph; wrap the lines however you like, the app collapses
them to a single string. Changes take effect on the next app start.

## question
Can this code ever be fully tested?

## grade.rubric
The grade is verifiability first, by a rule we publish rather than hide. The verdict sets the tier: <strong>CANNOT &rarr; F</strong> (some state is provably unbounded, so no finite test suite covers it), <strong>MIGHT &rarr; D</strong> (some state is undetermined). When every piece of state is finitely testable, the audit checks below decide <strong>A, B, or C</strong> by weighted health &mdash; god-files and type-escapes weigh most (3 each), then CI (2), then containers, pre-commit, and formatting (1 each). The number is the share of state that is finitely testable. No hidden weights.

## label.practical
test runs cover every path through the code, both sides of every yes-or-no. This is the whole list you would work through.

# --- GREEN: definitely testable ---------------------------------------------

## headline.can
This code definitely CAN be exhaustively tested.

## detail.can
None of the data this code keeps can grow without limit, so a fixed number of tests can check every case. The Slop Audit worked out the fewest test runs that reach every path: {cover} runs cover them all.

## detail.can_nocover
None of the data this code keeps can grow without limit, so a fixed number of tests can check every case. Run the [CLI](https://github.com/openhonest/slop-audit) to get the exact number of runs that cover every path.

# --- YELLOW: might be testable ----------------------------------------------

## headline.might
This code MIGHT be able to be exhaustively tested.

## detail.might
Nothing here is clearly endless, but we could not be sure. Some data gets handed to code we cannot follow: it is chosen while the program runs, or looked up by name, so we cannot list the values it might take. Fix the items below and you get a clear yes or no.

## culprits.heading.might
What you would have to fix

## culprits.note.might
For each of these, the data is passed to something we cannot follow (a call chosen while the program runs, or a lookup by name). Make that part concrete, or limit the data to a fixed set of values, and each one turns into a clear yes or no.

# --- RED: cannot be tested --------------------------------------------------

## headline.cannot
This code mathematically CANNOT be exhaustively tested.

## detail.cannot
{n} {plural} of data here can be almost anything, and the code makes decisions based on it. Because it can be anything, there is always one more case to check, so no fixed number of tests can ever cover them all. Writing more tests will not fix this. The only fix is to limit what that data can be, or stop letting other parts of the code change it.

## culprits.heading.cannot
What makes it impossible

## culprits.note.cannot
Each of these is data that can be almost anything, used to make a decision. Limit it to a fixed set of values, or stop letting other code change it, and it becomes testable.

## detail.na
Point it at a public repository with code in a language the analyzer reads: Python, TypeScript, JavaScript, Java, C#, Rust, Ruby, Go, or C.

# --- Share text -------------------------------------------------------------

## share.cannot
{slug}: fully testing it would take an endless number of tests. Some of its data can be almost anything, and the code makes decisions on it, so no fixed set of tests can cover every case. slopaudit.org

## share.might
{slug} might be fully testable. Nothing in it is clearly endless, but some data gets handed to code we cannot follow. slopaudit.org

## share.can
{slug} passes the Slop Audit: none of its data can grow without limit, so a fixed number of tests can cover every case. slopaudit.org

## share.na
I ran {slug} through the Slop Audit. slopaudit.org

# --- The two metric groups --------------------------------------------------

## group.core.title
Can this code be verified?

## group.core.note
The numbers behind the answer above. They carry no compliance tag on purpose: they set the ceiling on what every check below can ever prove.

## group.audit.title
How it maps to your audit

## group.audit.note
Each row below is matched to the enterprise audit areas and the compliance controls they answer to.

## scoped.why
Docs, build and test tooling, and loose entry-point scripts are not the code under test. Everything set aside is listed so you can check it.

## footer.fine
A full Slop Audit scores all 18 enterprise compliance dimensions and produces SOC 2 evidence as a byproduct. This page runs the static Layer 1 indicators only. It never executes the repo's code.

# --- Metric names and plain-language meanings -------------------------------

## label.L1.18
How much depends on hidden state

## tech.L1.18
L1.18 · mutable-state ratio

## meaning.L1.18
The share of functions whose behavior depends on data they don't own. The more there are, the more the code reaches outside itself, which predicts race conditions, flaky tests, and stale-cache bugs.

## label.L1.19
Decisions that could be exhaustively checked

## tech.L1.19
L1.19 · decision-space coverage

## meaning.L1.19
How many decisions in the code (branches, lookups, and the like) could be listed and checked one by one. What share your tests actually reach is the real number, and getting it means running your test suite, which this tool never does. Run the [CLI](https://github.com/openhonest/slop-audit) on your machine for that figure.

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

# --- Thread-safety surface --------------------------------------------------

## thread.heading
Thread-safety surface

## thread.blurb.exposed
Places where the compiler's thread-safety guarantee is overridden by hand or absent, with no visible guard: {exposed}. Each is a site to verify under free-threading, not a proven race. Removing the GIL turns state that was serialized by accident into state that runs at the same time.

## thread.blurb.review
No hand-overrides of the thread-safety guarantee. Lower-severity footguns worth a look (relaxed atomic ordering, mutable default arguments, shared state that sits behind a lock we could not tie to it): {review}.

## thread.blurb.clean
No concurrency escape hatches found. Nothing overrides or bypasses the language's own thread-safety guarantee.

## thread.blurb.na
Not analyzed for {lang} yet. The surface meter currently reads Rust and Python; other languages fall back to no result rather than a guess.

## thread.note
This measures audit surface, not races. It shows where a language's thread-safety guarantee is overridden or missing, so a human or a runtime tool knows where to look. It does not detect data races: that needs [ThreadSanitizer](https://doc.rust-lang.org/beta/unstable-book/compiler-flags/sanitizer.html#threadsanitizer) or an equivalent at runtime. A site here means "verify this", never "a race exists".

# --- Landing page -----------------------------------------------------------

## hero.kicker
The Slop Audit · an open standard

## hero.title
Can your code ever be fully tested?

## hero.sub
Paste a link to any public GitHub repo. We tell you one of three things: it can be fully tested, it might be, or it never can, and we show you why. A lot of AI-written code keeps shared data that can be almost anything; once that is true, no amount of testing can cover every case. Nothing is installed. We never run your code.

## hero.langs
Reads nine languages

## example.note
Here's a real result for our own code. Paste any public repo above to check yours.

## try.text
run the example on

## explain.title
What you're looking at

## explain.body
The top of the card is the answer: can this code be fully tested, yes, maybe, or no. Below it, each row is one thing we measured, matched to the audit checkboxes (SOC 2, NIST, OWASP, ISO) your reviewers already use.
