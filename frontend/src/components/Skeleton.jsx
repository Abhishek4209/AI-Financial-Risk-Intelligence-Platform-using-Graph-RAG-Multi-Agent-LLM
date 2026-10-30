export default function Skeleton({ variant = 'block', count = 1, height }) {
  const items = Array.from({ length: count })
  return (
    <div className={'skeleton-group skeleton-group--${variant}'}>
      {items.map((_, index) => (
        <span className={'skeleton skeleton--${variant}'} style={height ? { height } : undefined} key={index
} />
      ))}
    </div>
  )
}
