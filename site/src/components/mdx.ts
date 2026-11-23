import Num from "./Num.astro";
import Stat from "./Stat.astro";
import StatRow from "./StatRow.astro";
import Status from "./Status.astro";
import DataTable from "./DataTable.astro";
import Figure from "./Figure.astro";
import Note from "./Note.astro";
import Chart from "./Chart.astro";
import ArchDiagram from "./ArchDiagram.astro";
import RepairStepper from "./RepairStepper.astro";
import Chip3D from "./Chip3D.astro";
import LargeMemory from "./LargeMemory.astro";
import Commands from "./Commands.astro";

/** Components available inside MDX content without imports. */
export const mdxComponents = {
  Num, Stat, StatRow, Status, DataTable, Figure, Note, Chart,
  ArchDiagram, RepairStepper, Chip3D, LargeMemory, Commands,
};
