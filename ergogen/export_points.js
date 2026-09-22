// Flatten Ergogen's debug points.yaml for scripts/place_from_ergogen.py (KiCad's bundled Python has no
// YAML parser; Ergogen already ships js-yaml). One run holds both halves: a point is on the Right half when
// Ergogen mirrored it, and its ref is the part's reference in the half sheet, which both halves share.
//   points.json  keys:   {name, half, ref: SW<row><col>, x, y, r, combo, led}
//   mounts.json  mounts: {name, half, ref: H1-H5 / J1-J3, x, y, r}   (points carrying mount_ref)
const fs = require('fs')
const path = require('path')
const yaml = require('js-yaml')

const out = path.join(__dirname, 'output')
const points = yaml.load(fs.readFileSync(path.join(out, 'points', 'points.yaml'), 'utf8'))
const half = p => p.meta.mirrored ? 'Right' : 'Left'

const mounts = Object.entries(points)
    .filter(([, p]) => p.meta.mount_ref !== undefined)
    .map(([name, p]) => ({name, half: half(p), ref: p.meta.mount_ref, x: p.x, y: p.y, r: p.r}))

const keys = Object.entries(points).filter(([, p]) => p.meta.mount_ref === undefined).map(([name, p]) => {
    if (p.meta.row_code === undefined || p.meta.col_index === undefined) {
        throw new Error(`point ${name} is missing row_code/col_index`)
    }
    if (!['north', 'east', 'south', 'west'].includes(p.meta.led)) {
        throw new Error(`point ${name} needs led: north|east|south|west, got ${p.meta.led}`)
    }
    return {
        name,
        half: half(p),
        ref: `SW${p.meta.row_code}${p.meta.col_index}`,
        x: p.x,
        y: p.y,
        r: p.r,
        combo: Boolean(p.meta.combo),
        led: p.meta.led,
    }
})

for (const [list, what] of [[keys, 'key'], [mounts, 'mount']]) {
    const seen = list.map(p => `${p.half} ${p.ref}`)
    const dupes = seen.filter((k, i) => seen.indexOf(k) !== i)
    if (dupes.length) throw new Error(`duplicate ${what} references: ${dupes.join(', ')}`)
}

fs.writeFileSync(path.join(out, 'points.json'), JSON.stringify(keys, null, 2))
fs.writeFileSync(path.join(out, 'mounts.json'), JSON.stringify(mounts, null, 2))
console.log(`wrote ${keys.length} key points and ${mounts.length} mount points to ${path.relative(__dirname, out)}/`)
