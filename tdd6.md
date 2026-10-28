# TDD Talk Preparation
## TODO
1. Topics
2. Invitation
3. Presentation
4. Translate Romanian - not needed

Notes:
- Add stop-and-show at '+++'. Otherwise each section is a page

### Topics

- theory
- practice - code samples
- real experiences

### Invitation

<pre>
Hi all,

When do tests help us change code with confidence, and when do they become an obstacle?
What does **Test-Driven Development (TDD)** offer as a design and development practice? And what changes when AI agents write both the code and the tests?

I'd like to invite you to a session, and hopefully an open discussion, about TDD, drawing on practical experiences, both positive and constructive.

**We'll cover:**

1. What is TDD? The purpose of TDD and the RED > GREEN > REFACTOR cycle.

2. TDD in the Agentic Era: the role of tests and developers when working with AI agents.

3. TDD: The Good, the Bad and the Ugly: What works well and where things can go wrong at each stage of the cycle.

4. Beyond TDD: Testing Approaches and Trade-offs: Test-at-end, acceptance testing, BDD, internal testing, mocking libraries and UI testing, including their benefits, costs and potential pitfalls.

5. Practices That Complement TDD: XP, pair programming, trunk-based development, DDD, hexagonal architecture, clean code, and design principles such as DRY, OCP and SRP.

The goal is simple: how can we write tests with minimum effort while getting maximum value from them?

Questions and experiences from your own projects are very welcome, including those situations where tests may have caused more headaches than help.

At the end, we can also identify topics for future sessions based on real challenges and experiences from our projects.
</pre>

### Prepare

> Paste each question and its options as separate Teams messages, so people can react to their preferred answer.

To help tailor the TDD session, please react to one answer per question.

1. How much have you used TDD?
- Never tried it.
- Tried it, but rarely use it.
- Use it regularly.

2. When do you usually write automated tests?
- Before implementing the behavior.
- During or after implementation.
- Rarely write automated tests.

3. What is your biggest frustration with testing?
- Writing tests takes too much effort.
- Tests break when I change or refactor code.
- Tests pass, but bugs still reach production.

4. How do you use AI for development?
- I don't currently use it.
- For suggestions or generating code and tests.
- I delegate tasks to an agent that edits code and runs tests.

5. What would you most like from this session?
- Understand TDD through a practical example.
- Make tests simpler and easier to maintain.
- Explore TDD when working with AI agents.

6. Which language do you mainly use?
- Java / Kotlin / Scala
- JavaScript / TypeScript
- Other - please reply with the language.

7. Which testing libraries or frameworks do you use?
- junit
- mockito
- assertj
- playwright, cucumber
- ...

# TDD Talk

## Content

TDD Talk
2026-10-28
Costin Grigore
DB Engineering Coach

+++
Test Infected 2001 through XP.
Test Infected = I need tests to clarify when is done: the bug, the feature.

## Summary
1. What is TDD? RED > GREEN > REFACTOR cycle
2. TDD in the Agentic Era
3. TDD The Good, the Bad and the Ugly
4. Beyond TDD
5. Complementing Practices
6. Questions, experiences, next sessions
7. Resources


## 1. What is TDD? The purpose of TDD and the RED > GREEN > REFACTOR cycle.

### 1.1 Why tests? Do we need them?

- Code -> Tests
  - scafolding to help out
  - quality
  - acceptance
  - post change tests
- There are many ways to pair code with tests

+++

- Human
  - Code
    - On every change we throw away past manual testing.
  - Tests
    - Fragile.
    - Tests are tightly coupled to the implementation.
    - Too many.
    - Coverage. Proper coverage?
    - Tedious.
    - Copy-paste: breaks DRY (Don't Repeat Yourself).
    - Too complex: conditionals inside tests.
    - Take time.
    - Need external dependencies.
- AI
  - Code
    - More code.
    - Better quality?
    - Bugs fixed through regeneration.
      - Prompt is the new spec. Is it better?
    - Manual testing?
    - No test if it is regenerated?
  - Tests
    - No abstraction.
    - Deleting/changing regression tests just to pass.
    - Reflection-based tests to circumvent private methods.

### 1.2 Were did all started?

- Agile movement
- Test-driven development : by example : Beck, Kent 2002
  - https://archive.org/details/est-driven-development-by-example/test-driven-development-by-example/
- Still works now, also with AI
- Part of eXtreme Programming practices:
  ![xp practices](xp-practices.png)

### 1.3 TDD Cycle: RED-GREEN-REFACTOR

TDD is practice - https://newsletter.kentbeck.com/p/canon-tdd
![red green refactor cycle](red-green-refactor.png)

RED - Write a test, make it compile, run to confirm it fails.
  - There are tests that always pass. We want to be sure we first fail (including compilation errors).

GREEN - Write the simplest code to make the test pass.
  - Sins allowed: hacks, duct tape programming, copy-paste, and other shortcuts are allowed.
  - YAGNI. Don't overengineer. No analysis paralysis.

REFACTOR - Refactor the code to remove duplication.
  - Keep the test green.
  - Respect: YAGNI, OCP, and other principles, no code smells, and other good practices.

+++

Different phases have different purposes/focus:
- RED: prove missing functionality without knowing/passing implementation details
- GREEN: add new functionality as fast as possible (hacking around, duplicate code, whatever works to fix)
- REFACTOR: clean up the solution (good practices, remove code smells, clean code, clean design)

### 1.4 A sample

Requirement:
> Given a company group(division, organization, department), show its direct child groups and the number of projects directly contained in each child group.

```java
@Test
void showsChildGroupsWithTheirDirectProjectCounts() {
    //var directory = ProjectDirectory.of(); //1
    var directory = ProjectDirectory.of("uat-datasource1"); //2

    try {
        directory.createGroup("Technology");
        directory.createGroup("Engineering", "Technology");
        directory.createGroup("Finance", "Technology");

        directory.addProject("Engineering", "Atlas");
        directory.addProject("Engineering", "Orion");
        directory.addProject("Finance", "Ledger");

        assertThat(directory.childGroupsOf("Technology"))
            .containsExactlyInAnyOrder(
                GroupSummary.of("Engineering", 2),
                GroupSummary.of("Finance", 1)
            );
    } finally {
        // Cleanup //3
        directory.deleteGroupRecursively("Technology");
    }
}
```

### 1.5 What is the unit from unit testing ?

A good/canon TDD
- design tool
- grows a regression test suite
- feel safe to refactor (enables YAGNI and OCP) - refactoring is first class concept

More on what is a **unit**
- https://blog.stevensanderson.com/2009/08/24/writing-great-unit-tests-best-and-worst-practises/

A facade to something that acts as a unit. A responsibility.

### 1.6 Where do we cut?

Top-down units ⇒ Test-Driven Design.

- Split it when it breaks and when we need to search through it.
- We don't want to know the details: whatever works for the unit.

```mermaid
flowchart TD
    U1[Unit 1] --> U11[Unit 1.1]
    U1 --> U12[Unit 1.2]
    U1 --> U13[Unit 1.3]
    U1 --> U14[Unit 1.4]
    U13 --> U131[Unit 1.3.1]
    U13 --> U132[Unit 1.3.2]
    U132 -.-> U132b[Unit 1.3.2b]
    style U132 text-decoration:line-through
```

#### Spawning a unit test

So we have a test that fails.
We might want to expose an internal detail of the unit and make assertions on it. Is thightly coupled to the implementation internal details. If that sub-unit component is complex or is used in other parts of the system it can become a unit on its own. If is simple the current test should be enough definition of success.

Principles

- Encapsulation
- Divide and conquer
- YAGNI
- Tell, Don't Ask

#### Entrypoint to unit

Test in TDD is **developer test**.
The unit is the thing that has a facade.
With a test we want to exercise the behavior of the system. 

Some classes are implementation details of the unit and some advocate to delete tests used for the internal implementation.

The facade/API has usually 4 types of operations that act in concert:
- factory/lookup - to get access to a unit
- functions - compute something
- query - to observe the state
- commands - to change the state

Usually our tests need first to get access to a unit, then to query it, and finally to command it.

So naturally we will grow the tests on the most complex parts of the unit.

### 1.7 Anathomy of a good unit test

1. Get access to the unit.
2. Move the unit to a known state
   - Should not depend on past runs (the test before could even crash so the cleanup before is not guaranteed to be executed).
3. Query the unit to assert the state is as expected.
4. Command the unit to change its state.
5. Query the unit to assert the state is as expected.
6. ~~Cleanup the unit to a known state.~~
   - Cleanup is not warranted (the system could crash, or end in the middle of the test).
   - Cleanup would create the impression that the other tests are safe to run after this one and that they don't need to be isolated. But they do.
   - Cleanup will block investigations of the state of the unit after a test has run.


```java
@Test
void showsChildGroupsWithTheirDirectProjectCounts() {
    var directory = ProjectDirectory.of("uat-datasource1");

    // Establish a known initial state, even if a previous run crashed.
    directory.deleteGroupRecursively("Technology");
    directory.createGroup("Technology");

    assertThat(directory.childGroupsOf("Technology")).isEmpty();

    directory.createGroup("Engineering", "Technology");
    directory.createGroup("Finance", "Technology");

    directory.addProject("Engineering", "Atlas");
    directory.addProject("Engineering", "Orion");
    directory.addProject("Finance", "Ledger");

    assertThat(directory.childGroupsOf("Technology"))
        .containsExactlyInAnyOrder(
            GroupSummary.of("Engineering", 2),
            GroupSummary.of("Finance", 1)
        );
}
```

`deleteGroupRecursively` should tolerate a missing group. This assumes `"Technology"` is reserved for this test and concurrent runs do not share it.

+++

With a real database:

- Minimal input information, expressed in concepts ⇒ no accidental complexity.
- Clear output.

Emergent properties

- Testable code.
- Composable.
- Instantiable.
- Fast.
- Focus on the first problem.

Opens doors for explorable code.

Clear errors provide guidance. See Git errors.

+++ 

- Use AssertJ in Java and Kotlin.
- Better than mock, stub, or fake ⇒ lazy-load real database
- Prefer constructor injection - works with dependency injection containers but also manuall (even without annotations).
  - Forces better design in wiriging.
- Use a facade to instantiate the unit.

## 2. TDD in the Agentic Era

> The role of tests and developers when working with AI agents.
(!) Agree on the behavior. Let the agent find a solution. Use the tests to protect the behavior while improving the design. We need to decide what is a good TDD and a good test.

++

- See John Smart presentation - []()
- Also there a set of skills and prompts on tdd: /discover /acceptance /design /tdd /review

### 2.1 Test smell: cleanup at end
As in code above even after describing an anathomy of a good test.

```java
@Test
void showsChildGroupsWithTheirDirectProjectCounts() {
    //var directory = ProjectDirectory.of(); //1
    var directory = ProjectDirectory.of("uat-datasource1"); //2

    try {
        directory.createGroup("Technology");
        directory.createGroup("Engineering", "Technology");
        directory.createGroup("Finance", "Technology");

        directory.addProject("Engineering", "Atlas");
        directory.addProject("Engineering", "Orion");
        directory.addProject("Finance", "Ledger");

        assertThat(directory.childGroupsOf("Technology"))
            .containsExactlyInAnyOrder(
                GroupSummary.of("Engineering", 2),
                GroupSummary.of("Finance", 1)
            );
    } finally {
        // Cleanup //3
        directory.deleteGroupRecursively("Technology");
    }
}
```

### 2.2 Test Smell: reflection-based tests to circumvent private methods.
> What if the deleteGroupRecursively is private?

```java
@Test
void showsChildGroupsWithTheirDirectProjectCounts() throws Exception {
    var directory = ProjectDirectory.of("uat-datasource1");

    // "Fix": bypass encapsulation to establish the initial state.
    var cleanup = directory.getClass()
        .getDeclaredMethod("deleteGroupRecursively", String.class);
    cleanup.setAccessible(true);
    cleanup.invoke(directory, "Technology");

    directory.createGroup("Technology");

    assertThat(directory.childGroupsOf("Technology")).isEmpty();

    directory.createGroup("Engineering", "Technology");
    directory.createGroup("Finance", "Technology");

    directory.addProject("Engineering", "Atlas");
    directory.addProject("Engineering", "Orion");
    directory.addProject("Finance", "Ledger");

    assertThat(directory.childGroupsOf("Technology"))
        .containsExactlyInAnyOrder(
            GroupSummary.of("Engineering", 2),
            GroupSummary.of("Finance", 1)
        );
}
```

### 2.3 Mocking

- Mocking database when is simpler to just use a real inmemory or file based transient database

+++
With Mockito, the same test might become this, assuming the directory delegates the query to a repository:

```java
@Test
void showsChildGroupsWithTheirDirectProjectCounts() {
    var repository = mock(ProjectRepository.class);
    var directory = ProjectDirectory.of(repository);

    when(repository.childGroupsOf("Technology"))
        .thenReturn(List.of(
            GroupSummary.of("Engineering", 2),
            GroupSummary.of("Finance", 1)
        ));

    assertThat(directory.childGroupsOf("Technology"))
        .containsExactlyInAnyOrder(
            GroupSummary.of("Engineering", 2),
            GroupSummary.of("Finance", 1)
        );
}
```

+++
**Now the test supplies the answer it expects.** It may verify delegation, but it no longer verifies creating groups, assigning projects or calculating their counts. A broken repository query could still pass this test.

If the directory performs the counting itself, the mock could supply raw groups and projects instead. That tests more behavior, but couples the setup to the repository interactions.

Injection itself is useful. **The question is which behavior you replace when you inject a mock.**

### 2.4 Other Test Smell

- Deleting/changing regression tests just to pass.
- No abstraction.

### 2.5 Other Test Smells that AI agrees on

Many are existing test smells that agents can produce **quickly and convincingly**. Some recognizable examples:

| Smell | What the agent does | Why it is a problem |
|---|---|---|
| **Testing its own assumptions** | Generates implementation and tests from the same misunderstanding. | Both agree, but the required behavior is wrong. |
| **Expected copied from actual** | Runs the implementation and pastes its output into the assertion. | Observed behavior becomes the specification without validation. |
| **Mocking the answer** | Stubs the repository with exactly the result being asserted. | The behavior supposedly tested has been replaced. |
| **Mocking the subject** | Stubs the method under test, sometimes through a spy. | The test bypasses the implementation it should exercise. |
| **Reflection escape hatch** | Accesses private methods or fields to make setup or assertions easier. | The test becomes coupled to internal structure. |
| **Assertion erosion** | Replaces exact results with `isNotNull()`, `isNotEmpty()` or partial matching. | The test becomes green by losing relevant checks. |
| **Swallowed failures** | Catches exceptions, logs them and lets the test finish successfully. | Failure no longer produces a red test. |
| **Skipping obstacles** | Disables a failing test or adds an assumption that skips it. | The suite appears healthy because evidence disappeared. |
| **Production changes for test convenience** | Adds public setters, test flags or alternate branches solely to accommodate tests. | Test setup starts dictating inappropriate production behavior. |
| **Testing framework behavior** | Tests getters, constructors or mock responses instead of meaningful application behavior. | More tests create little additional confidence. |
| **Excessive verification** | Verifies every internal call, call count and order. | Harmless implementation changes break tests. |
| **Duplicated test machinery** | Generates elaborate builders, fixtures and helpers for a small scenario. | Understanding the test requires understanding another system. |
| **Timing patches** | Adds sleeps, retries or larger timeouts until a test passes. | Instability is hidden or made slower rather than explained. |
| **Environment mismatch** | Uses a substitute database whose behavior differs from production. | Passing tests miss relevant query, constraint or transaction behavior. |
| **Narrow validation presented as complete** | Runs only the new test, or only compilation, then reports success. | Existing regressions remain undiscovered. |
| **Tests that never ran** | Creates a test outside discovery conventions or uses an excluded tag. | A green build gives no evidence about that test. |
| **Unreviewed snapshot approval** | Regenerates snapshots after an unexpected failure. | Potential regressions are accepted in bulk. |

The particularly **agentic failure mode** is optimizing for the visible completion signal:

> **"Make the build green" can become "change whatever prevents the build from being green."**

Your agreed boundary test helps establish what must remain true while the agent searches for an implementation.

As you pointed out earlier, **changing assertions, snapshots or test setup is not automatically wrong**. The smell is making the change without explaining which requirement or assumption changed and why.

### 2.6 Guardrails

- First RED test with clear boundary. Design is done here.
- Make it GREEN while **KEEPING test boundary**: unit, unit api with input/output parameters
- If is needed to be changed evidence should be given (to human or other agentic role)
- Just refactor. Unfortunately we still don't have good TRUE REFACTORING tools as MCP. But they might come.
  - Here we are in the antiquity age: replace, full replace, sed, cat
- Anyway as we have green in our test and all other tests we at least have localized efect inside unit.

## 3. TDD The Good, the Bad and the Ugly

#### Things that are exposed as bad practices by TDD

- testing implementation details
- mocking
- testing query and command separately
- changing internal state via methods that are not part of the facade (is a white-box testing smell)
- tests that are not isolated and depend on the order of execution of other tests (is a white-box testing smell)

## 3. TDD: The Good, the Ugly, the Bad

> What works well and where things can go wrong at each stage of the cycle.

**The Good:** the cycle clarifies behavior, provides feedback and supports changes to the design.

**The Ugly:** we introduce unnecessary constraints, complexity or maintenance.

**The Bad:** we obtain a green result without establishing the intended behavior.

| Stage | The Good | The Bad | The Ugly |
|---|---|---|---|
| **RED** | Choose one behavior. Express it through a meaningful boundary. Establish the initial state and confirm the expected failure. | Write tests because a class or method exists. Specify internal interactions. Include irrelevant setup details. | The test never runs, always passes, or fails for an unrelated reason that we mistake for evidence of missing behavior. |
| **GREEN** | Find a simple working solution. Temporary shortcuts are acceptable. Check existing behaviors too. | Implement speculative requirements or abstractions. Make the step so large that failures become difficult to understand. | Mock the behavior being tested, swallow failures, or weaken expectations solely to accept an incorrect result. |
| **REFACTOR** | Improve production and test code while preserving behavior. Keep internal restructuring behind the tested boundary. | Leave costly duplication and complexity untouched. Abstract prematurely. Add tests automatically for every extracted internal class. | Change required behavior unintentionally, then update the tests to match and call it refactoring. |

#### Decisions that require judgment

- **Changing or weakening an assertion:** appropriate when the original expectation was wrong or unnecessarily restrictive. Explain which constraint is being removed and why.
- **Refactoring before implementing the next behavior:** appropriate while existing tests are green. Prepare the structure, then introduce the next behavior.
- **Deleting a test:** appropriate when its requirement is obsolete or its remaining value does not justify its cost.
- **Using a test double:** useful for controlling a boundary; check which real behavior it replaces and where that behavior is verified.
- **Extracting a smaller unit:** useful when a responsibility deserves its own contract. Extracting a private helper does not automatically create that need.
- **Stopping after GREEN:** cleanup is a judgment about the current design, not a requirement to invent a refactoring after every test.

#### Problems the cycle can expose

| Smell | What the feedback tells us |
|---|---|
| **Tests break when internals change, although behavior is preserved.** | Tests may be coupled to implementation details. |
| **We mock the repository's calculated answer and assert that same answer.** | We may only be checking delegation; the calculation remains unverified. |
| **A command test verifies `save()` was called; a query test returns a stubbed result.** | Neither establishes that the command's effect can actually be observed through the query. |
| **We use reflection or private-state manipulation to prepare the test.** | The test bypasses the public boundary and depends on internal structure. Reconsider the boundary or fixture. |
| **A test passes only after another test or a successful cleanup.** | It does not establish its own preconditions or isolation. |
| **Writing a small behavior test requires extensive setup.** | The API, fixture or responsibility boundary may need improvement. |
| **We cannot explain a test without reading implementation code.** | The test may not communicate the behavior it protects. |

#### Questions worth asking during the example

1. **What behavior are we agreeing on?**
2. **Does this test exercise that behavior, or replace it with a mock?**
3. **Can we change the implementation without changing the expectation?**
4. **If the expectation changes, what did we learn that justifies it?**

## 4. Beyond TDD

> Testing Approaches and Trade-offs: Test-at-end, acceptance testing, BDD, internal testing, mocking libraries and UI testing, including their benefits, costs and potential pitfalls.

#### Testign Myths

- We have a battery of tests and on mutation we can pinpoint the mutation by just looking at the tests. With what price? In writing tests and in maintaining them?
- Test coverage will help. Maybe if 100%, and maybe if we also have 100% branch coverage. That is not practical and rarely achievable. So we need strategic testing. Top down?

## 5. Complementing Practices
> XP, pair programming, trunk-based development, DDD, hexagonal architecture, clean code, and design principles such as DRY, OCP and SRP.

#### Things that go well with TDD

- DDD (Domain Driven Design) & Hexagonal Architecture.
  - we could use a persistance layer (whatever is faster to run and use)
    - database: embedded, in memory or a real one
      - real SQL queries/CRUD also get tested (think that native sql querries)
    - in memory data structures
- Clean Code
- Refactoring of Code Smells
  - Open Closed Principle. If we break tests then we don't respect the OCP.
  - A refactor keeps the tests green.
  - We are free to change the implementation details if the tests are green.


## 6. Questions, experiences, next sessions
> Questions and experiences from your own projects are very welcome, including those situations where tests may have caused more headaches than help.
> Topics for future sessions based on real challenges and experiences from our projects.

## 7. Resources

- https://www.google.com/search?q=TDD%2C+Where+Did+It+All+Go+Wrong&sourceid=chrome&ie=UTF-8&source=chrome.ctxt
- TDD, Where Did It All Go Wrong (Ian Cooper) - https://www.youtube.com/watch?v=EZ05e7EMOLM
- https://www.reddit.com/r/programming/comments/21fhy7/ian_cooper_tdd_where_did_it_all_go_wrong/
- https://archive.org/details/est-driven-development-by-example/test-driven-development-by-example/
- Dan North - https://dannorth.net/
- https://martinfowler.com/articles/are-harnesses-worth-the-cost.html
