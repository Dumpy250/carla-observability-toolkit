import { Fragment } from 'react'

function KeyValueGrid({ entries }) {
  return (
    <dl className="kv-grid">
      {entries.map((entry) => (
        <Fragment key={entry.key}>
          <dt>{entry.label}</dt>
          <dd>{entry.value}</dd>
        </Fragment>
      ))}
    </dl>
  )
}

export default KeyValueGrid
