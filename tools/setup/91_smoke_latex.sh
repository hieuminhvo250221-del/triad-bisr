#!/usr/bin/env bash
# Smoke test of the LaTeX toolchain: compile a small IEEEtran conference paper with the packages
# the real paper will use (this also warms Tectonic's package cache).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../env.sh"
W="$TRIAD_BUILD/smoke/latex"; mkdir -p "$W"; cd "$W"
cat > smoke.tex <<'TEX'
\documentclass[conference]{IEEEtran}
\usepackage{amsmath,amssymb,amsthm,graphicx,booktabs,multirow,cite,xcolor,siunitx}
\usepackage{algorithm,algpseudocode}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,fit,calc}
\usepackage{hyperref}
\newtheorem{theorem}{Theorem}
\begin{document}
\title{Toolchain Smoke Test}
\author{\IEEEauthorblockN{A. Author}\IEEEauthorblockA{Affiliation}}
\maketitle
\begin{abstract}Smoke test of the IEEEtran toolchain.\end{abstract}
\section{Math}
\begin{theorem}A fault store of $T = R + S(R+K) + K$ entries suffices.\end{theorem}
\begin{algorithm}\caption{Test}\begin{algorithmic}[1]\State $x \gets 0$\While{$x < 3$}\State $x \gets x + 1$\EndWhile\end{algorithmic}\end{algorithm}
\section{Figure and table}
\begin{figure}[h]\centering
\begin{tikzpicture}[node distance=8mm, box/.style={draw, rounded corners, minimum width=18mm, minimum height=7mm}]
\node[box] (a) {MBIST}; \node[box, right=of a] (b) {BIRA}; \node[box, right=of b] (c) {BISR};
\draw[-{Latex}] (a) -- (b); \draw[-{Latex}] (b) -- (c);
\end{tikzpicture}\caption{Blocks.}\end{figure}
\begin{table}[h]\centering\caption{Numbers}\begin{tabular}{lr}\toprule Item & Value\tabularnewline\midrule Area & \SI{0.19}{\milli\meter\squared}\tabularnewline\bottomrule\end{tabular}\end{table}
See \cite{demo}.
\begin{thebibliography}{1}\bibitem{demo} A. Author, ``Title,'' 2026.\end{thebibliography}
\end{document}
TEX
tectonic -X compile smoke.tex 2>&1 | grep -v -E '^note: (downloading|Running|Rerunning|Writing|Skipped)' | tail -8
ls -la smoke.pdf
