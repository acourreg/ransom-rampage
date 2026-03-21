export function computeLayout(nodes, svgWidth, svgHeight) {
  const NODE_W = 140, NODE_H = 70
  const cols = { entry: 0, human: 1, vendor: 1, middleware: 2, server: 2, database: 3 }
  const colX = [60, 240, 420, 600]

  // Group nodes by column
  const groups = [[], [], [], []]
  nodes.forEach(n => groups[cols[n.type] ?? 2].push(n))

  // Assign positions
  return nodes.map(n => {
    const col = cols[n.type] ?? 2
    const group = groups[col]
    const idx = group.findIndex(g => g.id === n.id)
    const y = (svgHeight / (group.length + 1)) * (idx + 1) - NODE_H / 2
    return { ...n, x: colX[col], y }
  })
}
