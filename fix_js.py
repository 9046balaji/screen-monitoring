import sys

with open('digiwell/src/api/digiwell.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for l in lines:
    if "export const getAddictionHeatmap" in l:
        break
    new_lines.append(l)

code = """
export const getAddictionHeatmap = async () => {
  if (USE_MOCK) {
    const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const dummy = [];
    for(let d=0; d<days.length; d++){
      for(let h=0; h<24; h++){
        let val = Math.random() * 60;
        let risk = val < 15 ? "Low" : val < 30 ? "Medium" : val < 60 ? "High" : "Very High";
        dummy.push({day: days[d], hour: h, value: Math.floor(val), riskLevel: risk});
      }
    }
    return dummy;
  }
  const res = await axios.get(`${BASE_URL}/addiction-heatmap`);
  return res.data;
}
"""

with open('digiwell/src/api/digiwell.js', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
    f.write(code)

