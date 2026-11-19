# Observable Architecture & Code Rules

Follow these rules whenever designing, modifying, or explaining code so control flow and data transformations stay transparent.

## 1. Contracts Before Implementation
For multi-file or architectural tasks, outline the data flow (`Input -> Stage -> Output`), module ownership, and boundary data schemas before writing leaf implementation code.

## 2. Linear Top-Level Orchestration
Keep top-level entry points and pipelines flat and readable like a table of contents (`step1() -> step2() -> step3()`). Avoid hiding execution flow behind deep class hierarchies, dynamic registries, or implicit callbacks unless required by the framework.

## 3. Explicit Typed Boundaries
Pass explicit, typed data contracts (Pydantic models, `@dataclass`, TypeScript interfaces, or structs) across module boundaries instead of untyped dictionaries or `any` blobs.

## 4. Inspectable Intermediate State
Prefer explicit stage inputs/outputs, boundary logging, or `--dry-run` / `--validate-only` modes over silent in-place mutations of global or shared state.

## 5. End-of-Task Data-Flow Trace
After completing any multi-file implementation or refactor, include a concise 4–8 line **Input → Output Trace** naming the exact `file:function` hops and data shapes a concrete input passes through.
