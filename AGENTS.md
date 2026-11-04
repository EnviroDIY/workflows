# AGENTS.md — Arduino Project Guidelines

## Project Overview

This project is a set of workflows for managing Arduino-based development and continuous integration tasks using GitHub Actions.
The workflows facilitate these tasks:

* Verifying library structure.
* Building Arduino projects with both the Arduino CLI and PlatformIO.
* Verifying completeness of documentation and building documentation for publication on GitHub Pages.
* Preparing releases.

---

## General Agent Instructions

* The local environment is a Windows environment.
  * Run commands using Windows Powershell 7, which is located at "C:\Program Files\PowerShell\7\pwsh.exe"
  * Use Windows PowerShell commands, not Linux shell commands.
* Make the **smallest change necessary** to accomplish the requested task, prioritizing the fewest files and functions touched, while still implementing a complete and correct fix.
* Always favor simple elegant coding structures with as little complexity as possible.
* Do not refactor unrelated code, rename unrelated symbols, reorganize files, or "clean up" existing code unless requested.
* Preserve existing behavior unless the requested change specifically requires changing it.
* Preserve existing inline comments and debugging printouts when modifying or refactoring code.
* Before changing a public class, function, macro, constructor, or other API, search the repository for existing uses and update affected examples and tests as necessary.
* Avoid breaking the public API unless the user explicitly requests a breaking change.
* Follow existing project conventions when adding new code. When conventions differ between files, follow the convention used in the file most similar to the one being modified.
* If a requested change conflicts with an existing project convention, explain the conflict and use the approach that best satisfies the user's explicit request.
* If a change would require a potentially breaking API decision and the user's intent is unclear, ask before proceeding.
* If testing cannot be performed, say so explicitly. Never claim that code was tested when it was not.

### Instruction Priority

When instructions conflict, use the following priority:

1. The user's explicit request.
2. Correctness and compatibility with the project's supported platforms.
3. The requirements in this file.
4. Existing implementation conventions.

When possible, preserve existing behavior and API compatibility.

---

## Workspace Structure

* The primary product of this workspace is the workflows in the `.github/workflows` folder.
* The `.github/workflows` folder contains the workflow definitions for building, testing, and managing the project.

* The workflow `.github/workflows/verify_library_structure.yaml` is responsible for verifying the structure of the library.
  * The directory `validation_scripts` contains scripts used by the `.github/workflows/verify_library_structure.yaml` workflow.

* The workflow `.github/workflows/build_documentation.yaml` is responsible for testing the completion of and building the project documentation with Doxygen.
  * The directory `doxygen_scripts` contains python and shell scripts used by the `.github/workflows/build_documentation.yaml` workflow as well as some required images and font files.

* The workflow `.github/workflows/build_examples.yaml` is responsible for building the example projects.
  * The workflows `.github/workflows/compile_arduino_cli.yaml` and `.github/workflows/compile_platformio.yaml` are children of the `.github/workflows/build_examples.yaml` workflow and handle the compilation for their respective platforms.
  * The workflows `.github/workflows/determine_library_source.yaml` and `.github/workflows/check_for_dependencies.yaml` are helper workflows used by the `.github/workflows/build_examples.yaml` workflow and the `.github/workflows/prepare_release.yaml` workflows.
  * The directory `build_scripts` contains python and shell scripts used by the `.github/workflows/build_examples.yaml` workflow as well as some json mapping files.

* The workflow `.github/workflows/prepare_release.yaml` is responsible for preparing a new release of the library.
  * The directory `release_scripts` contains scripts used by the `.github/workflows/prepare_release.yaml` workflow.

* The directory `childTemplates` contains template files that are meant to be copied and used as starting points for new Arduino libraries.

* The directory `pioScripts` contains mostly one-off and testing scripts.

* The `archive` folder contains outdated and non-working code.
  * Do not use archived code as a model for new code unless specifically instructed to do so.
  * Never modify archived files unless specifically requested to.
  * Archived code is not committed to the repository.
  * Never review code in the archive folder.

<!-- cSpell:ignore RTTI -->
