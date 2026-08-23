import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ImageSorter } from "./ImageSorter";
import { useProjectStore, type ProjectAsset } from "@/store/projectStore";

function makeAsset(name: string): ProjectAsset {
  return {
    clientId: name,
    file: new File(["x"], name, { type: "image/jpeg" }),
    previewUrl: `blob:${name}`,
    status: "uploaded",
  };
}

beforeEach(() => {
  useProjectStore.setState({ projectId: "p1", assets: [makeAsset("a.jpg"), makeAsset("b.jpg"), makeAsset("c.jpg")] });
});

describe("ImageSorter", () => {
  it("renders thumbnails in store order", () => {
    render(<ImageSorter />);
    const images = screen.getAllByRole("img");
    expect(images.map((img) => img.getAttribute("alt"))).toEqual(["Frame 1", "Frame 2", "Frame 3"]);
  });

  it("removes an asset from the store when its remove button is clicked", async () => {
    render(<ImageSorter />);
    await userEvent.click(screen.getByLabelText("Remove frame 2"));
    expect(useProjectStore.getState().assets.map((a) => a.clientId)).toEqual(["a.jpg", "c.jpg"]);
  });

  it("reorders assets via the store's reorderAssets action", () => {
    useProjectStore.getState().reorderAssets(0, 2);
    expect(useProjectStore.getState().assets.map((a) => a.clientId)).toEqual(["b.jpg", "c.jpg", "a.jpg"]);
  });
});
