# ECB Tone Monitor

ECB Tone Monitor is a small experimental dashboard on the tone of ECB speeches.
It tracks whether speeches look more hawkish, dovish, or balanced over time.

## Data

The speeches come from the CBS Speeches dataset.
This public version focuses on a limited sample of ECB communication from 2019 to 2023, centered on Christine Lagarde and Isabel Schnabel.

## Method

Each speech is reduced to a simple hawkish/dovish score.
In this lightweight version, the score is produced with a local keyword-based heuristic designed to capture monetary-policy language such as inflation, tightening, easing, downside risks, or rate cuts.

The goal is not to claim a definitive measure of policy stance, but to provide a compact exploratory signal that can be visualized and compared across speeches and over time.

## Dashboard

The site shows:

- a timeline of average tone over time
- a score distribution
- speaker-level summaries
- the most hawkish and most dovish speeches in the sample
- a sortable table of all scored speeches

This is an experimental project and should be read as a simple research-style visualization, not as a production index.
