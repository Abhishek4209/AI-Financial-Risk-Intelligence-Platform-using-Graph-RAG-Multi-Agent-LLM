export default function ShapDriverChart({ drivers = [] }) {
if (!drivers.length) return <p className="empty-state">No SHAP factors were returned for this prediction.</p>
const maxMagnitude = Math.max(...drivers.map((driver) => Math.abs(driver.shap_value)), 0.0001)
return (
<div className="shap-chart" aria-label="Top model factors driving this prediction">
{drivers.map((driver) => {
const widthPercent = (Math.abs(driver.shap_value) / maxMagnitude) * 100
const positive = driver.shap_value >= 0
return (
<div className="shap-row" key={driver.feature}>
<span className="shap-row__label">{driver.feature.replaceAll('_', ' ')}</span>
<div className="shap-row__track">
<span
className={`shap-row__bar ${positive ? 'shap-row__bar--up' : 'shap-row__bar--down'}`}
style={{ width: `${widthPercent}%` }}
/>
</div>
<span className={`shap-row__value ${positive ? 'shap-row__value--up' : 'shap-row__value--down'}`}>
{positive ? '+' : ''}{driver.shap_value.toFixed(4)}
</span>
</div>
)
})}
</div>
)
}
