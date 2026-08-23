"use client";

import { DndContext, closestCenter, type DragEndEvent, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import { SortableContext, rectSortingStrategy, useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useProjectStore, type ProjectAsset } from "@/store/projectStore";

function SortableThumb({ asset, index }: { asset: ProjectAsset; index: number }) {
  const removeAsset = useProjectStore((s) => s.removeAsset);
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: asset.clientId,
  });

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.5 : 1 }}
      className="relative aspect-square touch-none select-none overflow-hidden rounded-lg border border-foreground/10"
      {...attributes}
      {...listeners}
    >
      {/* eslint-disable-next-line @next/next/no-img-element -- object URLs aren't supported by next/image */}
      <img src={asset.previewUrl} alt={`Frame ${index + 1}`} className="h-full w-full object-cover" />
      <span className="absolute left-1 top-1 rounded bg-black/60 px-1.5 py-0.5 text-xs text-white">{index + 1}</span>
      <button
        type="button"
        aria-label={`Remove frame ${index + 1}`}
        onPointerDown={(e) => e.stopPropagation()}
        onClick={() => removeAsset(asset.clientId)}
        className="absolute right-1 top-1 rounded-full bg-black/60 px-1.5 py-0.5 text-xs text-white hover:bg-black/80"
      >
        ×
      </button>
      {asset.status === "error" && (
        <span className="absolute inset-x-0 bottom-0 bg-red-600/90 px-1 py-0.5 text-center text-xs text-white">
          Upload failed
        </span>
      )}
    </div>
  );
}

export function ImageSorter() {
  const assets = useProjectStore((s) => s.assets);
  const reorderAssets = useProjectStore((s) => s.reorderAssets);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const fromIndex = assets.findIndex((a) => a.clientId === active.id);
    const toIndex = assets.findIndex((a) => a.clientId === over.id);
    if (fromIndex === -1 || toIndex === -1) return;
    reorderAssets(fromIndex, toIndex);
  }

  if (assets.length === 0) return null;

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={assets.map((a) => a.clientId)} strategy={rectSortingStrategy}>
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-4">
          {assets.map((asset, index) => (
            <SortableThumb key={asset.clientId} asset={asset} index={index} />
          ))}
        </div>
      </SortableContext>
    </DndContext>
  );
}
