import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { UploadZone } from "./UploadZone";
import { useProjectStore } from "@/store/projectStore";

function oversizedFile(): File {
  const file = new File(["x"], "huge.jpg", { type: "image/jpeg" });
  Object.defineProperty(file, "size", { value: 20 * 1024 * 1024 });
  return file;
}

beforeEach(() => {
  useProjectStore.setState({ projectId: null, assets: [] });
});

describe("UploadZone", () => {
  it("accepts a valid image drop and adds it to the store", async () => {
    render(<UploadZone />);
    const input = screen.getByLabelText(/upload face photos/i);
    const file = new File(["fake"], "face.jpg", { type: "image/jpeg" });

    await userEvent.upload(input, file);

    await waitFor(() => expect(useProjectStore.getState().assets).toHaveLength(1));
    expect(useProjectStore.getState().assets[0].file.name).toBe("face.jpg");
  });

  it("rejects an unsupported file type", async () => {
    render(<UploadZone />);
    const input = screen.getByLabelText(/upload face photos/i);
    const file = new File(["fake"], "notes.txt", { type: "text/plain" });

    // fireEvent bypasses the input's `accept` filtering that userEvent.upload emulates,
    // matching a real drag-and-drop drop (which isn't filtered by `accept` either) and
    // exercising react-dropzone's own JS-level rejection instead.
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/unsupported file type/i));
    expect(useProjectStore.getState().assets).toHaveLength(0);
  });

  it("rejects a file over the size limit", async () => {
    render(<UploadZone />);
    const input = screen.getByLabelText(/upload face photos/i);

    await userEvent.upload(input, oversizedFile());

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/over 15mb/i));
    expect(useProjectStore.getState().assets).toHaveLength(0);
  });
});
