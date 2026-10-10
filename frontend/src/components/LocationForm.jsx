export default function LocationForm({ location, onChange, labels }) {
  function submit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const latitudeValue = form.get("latitude");
    const longitudeValue = form.get("longitude");
    const latitude = Number(latitudeValue);
    const longitude = Number(longitudeValue);
    if (!latitudeValue || !longitudeValue || !Number.isFinite(latitude) || latitude < -90 || latitude > 90
      || !Number.isFinite(longitude) || longitude < -180 || longitude > 180) {
      onChange(null);
      return;
    }
    onChange({ latitude, longitude });
  }

  return (
    <form className="location-form panel" noValidate onSubmit={submit}>
      <label>
        {labels.latitude}
        <input name="latitude" type="number" min="-90" max="90" step="any" required defaultValue={location.latitude} />
      </label>
      <label>
        {labels.longitude}
        <input name="longitude" type="number" min="-180" max="180" step="any" required defaultValue={location.longitude} />
      </label>
      <button type="submit">{labels.updateLocation}</button>
    </form>
  );
}
