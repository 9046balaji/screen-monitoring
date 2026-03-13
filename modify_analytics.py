import sys

with open('digiwell/src/pages/Analytics.jsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    "import HeatmapChart from '../components/charts/HeatmapChart';",
    "import HeatmapChart from '../components/charts/HeatmapChart';\nimport AddictionHeatmap from '../components/charts/AddictionHeatmap';"
)

text = text.replace(
    "<HeatmapChart data={usageHeatmap} delay={0.3} />",
    "<HeatmapChart data={usageHeatmap} delay={0.3} />\n      <AddictionHeatmap delay={0.35} />"
)

with open('digiwell/src/pages/Analytics.jsx', 'w', encoding='utf-8') as f:
    f.write(text)
