const HEX_R_DEFAULT = 46
const LABEL_H = 28
const GAP_MIN = 18

export function computeLayout(nodes, svgW = 600, svgH = 320) {
  const n = nodes.length
  if (n === 0) return []

  const R = _adaptiveR(n, svgW, svgH)

  if (n <= 5) return _layoutCircle(nodes, svgW, svgH, R)
  if (n === 6) return _layoutHexStar(nodes, svgW, svgH, R)
  return _layoutLayered(nodes, svgW, svgH, R)
}

function _adaptiveR(nodeCount, W, H) {
  if (nodeCount <= 5)  return 48
  if (nodeCount <= 7)  return 44
  if (nodeCount <= 9)  return 40
  if (nodeCount <= 11) return 36
  return 32
}

function _layoutCircle(nodes, W, H, R) {
  const cx = W / 2, cy = H / 2
  const radius = Math.min(W, H) * 0.36
  return nodes.map((n, i) => {
    const angle = (2 * Math.PI * i / nodes.length) - Math.PI / 2
    return { ...n, cx: cx + radius * Math.cos(angle), cy: cy + radius * Math.sin(angle), r: R }
  })
}

function _layoutHexStar(nodes, W, H, R) {
  const cx = W / 2, cy = H / 2
  const dbIdx = nodes.findIndex(n => n.type === 'database')
  const centerIdx = dbIdx >= 0 ? dbIdx : 0
  const center = nodes[centerIdx]
  const others = nodes.filter((_, i) => i !== centerIdx)
  const radius = Math.min(W * 0.38, H * 0.38)
  const result = [{ ...center, cx, cy, r: R + 4 }]
  others.forEach((n, i) => {
    const angle = (2 * Math.PI * i / others.length) - Math.PI / 2
    result.push({ ...n, cx: cx + radius * Math.cos(angle), cy: cy + radius * Math.sin(angle), r: R })
  })
  return result
}

function _layoutLayered(nodes, W, H, R) {
  const TYPE_COL = { entry: 0, human: 1, vendor: 1, middleware: 2, server: 2, database: 3 }
  const NODE_TOTAL_H = R * 2 + LABEL_H

  const groups = {}
  nodes.forEach(n => {
    const col = TYPE_COL[n.type] ?? 2
    if (!groups[col]) groups[col] = []
    groups[col].push(n)
  })

  // 2+ databases → overflow into col 2
  const dbs = nodes.filter(n => n.type === 'database')
  if (dbs.length > 1) {
    dbs.slice(1).forEach(db => {
      if (groups[3]) groups[3] = groups[3].filter(x => x.id !== db.id)
      if (!groups[2]) groups[2] = []
      if (!groups[2].find(x => x.id === db.id)) groups[2].push(db)
    })
  }

  const occupiedCols = Object.keys(groups)
    .map(Number)
    .filter(c => groups[c]?.length > 0)
    .sort((a, b) => a - b)

  const colCount = occupiedCols.length
  const PAD_X = Math.max(R + 10, 55)
  const PAD_Y = Math.max(R + 10, 44)

  const availW = W - PAD_X * 2
  const colX = {}
  occupiedCols.forEach((col, i) => {
    colX[col] = colCount === 1
      ? W / 2
      : PAD_X + (i / (colCount - 1)) * availW
  })

  const availH = H - PAD_Y * 2
  const positioned = []

  occupiedCols.forEach(col => {
    const group = groups[col]
    const count = group.length

    const minSpacing = NODE_TOTAL_H + GAP_MIN
    const maxSpacing = 160
    const spacing = count === 1
      ? 0
      : Math.min(maxSpacing, Math.max(minSpacing, availH / (count - 1)))

    const totalH = (count - 1) * spacing
    const startY = H / 2 - totalH / 2
    const stagger = (col % 2 === 1 && count > 1 && count < 4) ? spacing * 0.3 : 0

    group.forEach((n, i) => {
      positioned.push({
        ...n,
        cx: colX[col],
        cy: startY + i * spacing + stagger,
        r: n.type === 'database' ? R + 3 : R,
      })
    })
  })

  return positioned
}

export function hexPoints(cx, cy, r) {
  return [0, 1, 2, 3, 4, 5].map(i => {
    const angle = (Math.PI / 3) * i - Math.PI / 6
    return `${(cx + r * Math.cos(angle)).toFixed(1)},${(cy + r * Math.sin(angle)).toFixed(1)}`
  }).join(' ')
}
