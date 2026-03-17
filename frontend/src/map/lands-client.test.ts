import { describe, expect, test, vi } from "vitest";

const { fetchJsonMock } = vi.hoisted(() => ({
  fetchJsonMock: vi.fn(),
}));

vi.mock("../http", () => ({
  fetchJson: fetchJsonMock,
}));

import { streamLandFeatures } from "./lands-client";

describe("streamLandFeatures", () => {
  test("resets mock state", () => {
    fetchJsonMock.mockReset();
    expect(fetchJsonMock).not.toHaveBeenCalled();
  });

  test("streams a single page and calls onBatch once", async () => {
    const onBatch = vi.fn();
    fetchJsonMock.mockReset();
    fetchJsonMock.mockResolvedValueOnce({
      type: "FeatureCollection",
      features: [{ type: "Feature", geometry: null, properties: { address: "a" } }],
      nextCursor: null,
    });

    await streamLandFeatures(onBatch);

    expect(fetchJsonMock).toHaveBeenCalledWith("/api/lands?limit=500", { timeoutMs: 20000 });
    expect(onBatch).toHaveBeenCalledTimes(1);
  });

  test("follows pagination until nextCursor is exhausted", async () => {
    const onBatch = vi.fn();
    fetchJsonMock.mockReset();
    fetchJsonMock
      .mockResolvedValueOnce({
        type: "FeatureCollection",
        features: [{ type: "Feature", geometry: null, properties: { address: "a" } }],
        nextCursor: "cursor-1",
      })
      .mockResolvedValueOnce({
        type: "FeatureCollection",
        features: [{ type: "Feature", geometry: null, properties: { address: "b" } }],
        nextCursor: null,
      });

    await streamLandFeatures(onBatch);

    expect(fetchJsonMock).toHaveBeenNthCalledWith(1, "/api/lands?limit=500", { timeoutMs: 20000 });
    expect(fetchJsonMock).toHaveBeenNthCalledWith(2, "/api/lands?limit=500&cursor=cursor-1", {
      timeoutMs: 20000,
    });
    expect(onBatch).toHaveBeenCalledTimes(2);
  });

  test("skips empty feature batches", async () => {
    const onBatch = vi.fn();
    fetchJsonMock.mockReset();
    fetchJsonMock
      .mockResolvedValueOnce({
        type: "FeatureCollection",
        features: [],
        nextCursor: "cursor-1",
      })
      .mockResolvedValueOnce({
        type: "FeatureCollection",
        features: [{ type: "Feature", geometry: null, properties: { address: "b" } }],
        nextCursor: null,
      });

    await streamLandFeatures(onBatch);

    expect(onBatch).toHaveBeenCalledTimes(1);
  });

  test("propagates fetch failures", async () => {
    fetchJsonMock.mockReset();
    fetchJsonMock.mockRejectedValueOnce(new Error("network"));

    await expect(streamLandFeatures(vi.fn())).rejects.toThrow("network");
  });
});
