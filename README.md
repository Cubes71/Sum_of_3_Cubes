Sum of Three Cubes Solutions List: +-- and -++ Families

This repository contains computed integer solutions to the Diophantine equations

X³ + (-Y)³ + (-Z)³ = n

and

(-X)³ + Y³ + Z³ = n

for positive integers n < 1000.

The solutions are organized by sections and section lines, which provide a structural way of viewing and comparing solutions across both sign families.

Ordering Convention

Throughout this repository, solutions are organized according to the absolute values of the variables. The signs appearing in the equations are used only when evaluating the cubic expressions and are ignored when determining sections and section lines.

The ordering convention is:

|X| > |Y| ≥ |Z| ≥ 0

This allows the same section structure to be used for both sign families.

Section Definition

For both sign families, define:

q = |X| − |Y|

s = |X| − |Z|

sl = |Y| − |Z| + 1

where:

q is the difference between the magnitudes of X and Y,
s is the section number,
sl is the section line.

Sections are determined solely by the difference between the absolute values of X and Z, while section lines are determined solely by the difference between the absolute values of (Y and Z) + 1.

Every solution belongs to exactly one section and one section line.

Example

For the solution:

X = 109, Y = -87, Z = -86

we use the magnitudes:

|X| = 109, |Y| = 87, |Z| = 86

Therefore:

q = 109 − 87 = 22

s = 109 − 86 = 23

sl = 87 − 86 + 1 = 2

n = 470

This solution is located in Section 23, Section Line 2.

The files contains solutions to:

X³ + (-Y)³ + (-Z)³ = n

and

(-X)³ + Y³ + Z³ = n

The same section and section-line definitions are used, allowing direct comparison with the +-- and -++ families.

Purpose

The purpose of this dataset is to study the structural organization of solutions to the sum-of-three-cubes problem. Sorting solutions by sections and section lines reveals patterns that are often difficult to observe when solutions are listed solely by their target value n.

Potential areas of investigation include:

Distribution of solutions across sections.
Distribution of solutions across section lines.
Growth of solution magnitudes.
Density of solutions as section number increases.
Persistence or disappearance of section lines.
Comparisons between the +-- and -++ sign families.
Structural relationships among q, s, and sl.

The data was generated computationally by the .py file and sorted by section to expose geometric and arithmetic patterns within the solution space.
