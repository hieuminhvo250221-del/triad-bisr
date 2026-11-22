# TRIAD-BISR

Embedded SRAM with built-in self-test and self-repair (MBIST + BIRA + BISR) whose redundancy-allocation
algorithm treats **spare rows, spare columns and ECC** as three jointly allocated resources.
Target: SkyWater sky130 with a real OpenRAM hard macro, taken from RTL to GDS with open-source tools.

- Plan, claimed contributions and decision gates: [`docs/00_plan.md`](docs/00_plan.md) (Vietnamese)
- Progress log: [`docs/STATUS.md`](docs/STATUS.md)
- Environment and tool versions: [`docs/env/ENVIRONMENT.md`](docs/env/ENVIRONMENT.md)
- How to run things: [`AGENTS.md`](AGENTS.md)

Status: environment ready; algorithm study in progress.
