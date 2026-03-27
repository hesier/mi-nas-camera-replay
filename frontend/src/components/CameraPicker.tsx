import type { CameraItem } from '../types/api';

interface CameraPickerProps {
  cameras: CameraItem[];
  selectedCameraNo: number | null;
  onSelectCamera: (cameraNo: number) => void;
}

export function CameraPicker({
  cameras,
  selectedCameraNo,
  onSelectCamera,
}: CameraPickerProps) {
  return (
    <label className="field-group compact-field-group">
      <span className="field-label">回放通道</span>
      <select
        aria-label="回放通道"
        className="field-input"
        value={selectedCameraNo ?? ''}
        onChange={(event) => onSelectCamera(Number(event.target.value))}
      >
        {cameras.map((camera) => (
          <option key={camera.cameraNo} value={camera.cameraNo}>
            {camera.label}
          </option>
        ))}
      </select>
    </label>
  );
}
