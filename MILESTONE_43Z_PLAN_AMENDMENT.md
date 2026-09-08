# M43Z pre-evaluation amendment: moderate OFF response controls

The initial public freeze was cdf2c8ca7154643b92c87742d207310a7fee304c.
No Z calibration shift, baseline detector execution or prospective trial had
been evaluated when this amendment was prepared. Only exact historical source
restoration, metadata geometry and synthetic composition tests had run.

A pre-evaluation analytical review identified a limitation of the strength4S
near-OFF controls. A narrow point spreads into broad filtered OFF responses
roughly as A/sqrt(width). With strength96 or192, these responses can already
exceed the reference's stacked threshold10 at broad widths and match a central
ON track within20 Hz. Consequently, strong nearby OFF can measure reference's
own signal cost while leaving too few reference-surviving inputs to measure
the added neighborhood cut. This is a design concern derived from fixed rules,
not an observed new-panel result or a guarantee about background-dependent scores.

Preserve the original320 case records and their indices exactly. Append32
matched distributed17 inputs with the same nearby OFF geometry but OFF strengthS
(24 or48), instead of4S. Each appended input has the same ON payload as its
original distributed17 signal-only counterpart and the same OFF carrier/epochs
as its strong near-OFF counterpart. This yields352 base inputs,224 signal-present,
128 pure controls and1,408 paired policy endpoints, plus the separate baseline.
There are128 matched signal/OFF payload comparisons. Report both moderate and
strong near-OFF levels without pooling away their strength difference.

No detector, threshold, calibration seed/rows, association, original input,
scientific gate or test definition changes. Original outcomes cannot be lost
because they had not yet been computed. The first freeze remains public history.
The amended plan, generator, runner, audit and full explicit configuration must
be public before any Z calibration or trial begins. The execution freeze is
the amendment commit, not the initial320-case commit.
