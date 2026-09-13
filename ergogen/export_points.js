// Flatten Ergogen's debug points.yaml into points.json for scripts/place_from_ergogen.py
// (KiCad's bundled Python has no YAML parser; Ergogen already ships js-yaml).
const fs = require('fs')
const path = require('path')
const yaml = require('js-yaml')

const out = path.join(__dirname, 'output')
const points = yaml.load(fs.readFileSync(path.join(out, 'points', 'points.yaml'), 'utf8'))

const keys = Object.entries(points).map(([name, p]) => {
    if (p.meta.row_code === undefined || p.meta.col_index === undefined) {
        throw new Error(`point ${name} is missing row_code/col_index`)
    }
    if (!['north', 'east', 'south', 'west'].includes(p.meta.led)) {
        throw new Error(`point ${name} needs led: north|east|south|west, got ${p.meta.led}`)
    }
    return {
        name,
        ref: `SW${p.meta.row_code}${p.meta.col_index}`,
        x: p.x,
        y: p.y,
        r: p.r,
        combo: Boolean(p.meta.combo),
        led: p.meta.led,
    }
})

const refs = keys.map(k => k.ref)
const dupes = refs.filter((r, i) => refs.indexOf(r) !== i)
if (dupes.length) throw new Error(`duplicate references: ${dupes.join(', ')}`)

fs.writeFileSync(path.join(out, 'points.json'), JSON.stringify(keys, null, 2))
console.log(`wrote ${keys.length} key points to output/points.json`)
