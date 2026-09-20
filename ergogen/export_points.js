// Flatten Ergogen's debug points.yaml into points.json for scripts/place_from_ergogen.py
// (KiCad's bundled Python has no YAML parser; Ergogen already ships js-yaml).
const fs = require('fs')
const path = require('path')
const yaml = require('js-yaml')

// output folder (relative to this file) as the first argument, default output/
const out = path.join(__dirname, process.argv[2] || 'output')
const points = yaml.load(fs.readFileSync(path.join(out, 'points', 'points.yaml'), 'utf8'))

// screw points carry mount_ref (H1..Hn) instead of a key's row_code/col_index: they place the
// schematic's mounting-hole footprints, not switches, so they go to their own file
const screws = Object.entries(points)
    .filter(([, p]) => p.meta.mount_ref !== undefined)
    .map(([name, p]) => ({name, ref: p.meta.mount_ref, x: p.x, y: p.y}))

const keys = Object.entries(points).filter(([, p]) => p.meta.mount_ref === undefined).map(([name, p]) => {
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

const mounts = screws.map(s => s.ref)
const mdupes = mounts.filter((r, i) => mounts.indexOf(r) !== i)
if (mdupes.length) throw new Error(`duplicate mounting-hole references: ${mdupes.join(', ')}`)

fs.writeFileSync(path.join(out, 'points.json'), JSON.stringify(keys, null, 2))
fs.writeFileSync(path.join(out, 'screws.json'), JSON.stringify(screws, null, 2))
console.log(`wrote ${keys.length} key points and ${screws.length} screw points to `
    + `${path.relative(__dirname, out)}/`)
