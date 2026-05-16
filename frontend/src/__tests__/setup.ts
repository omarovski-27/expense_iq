import "@testing-library/jest-dom";

// Stub localStorage so formatCurrency's localStorage read doesn't throw in jsdom
Object.defineProperty(window, "localStorage", {
  value: {
    getItem: () => null,
    setItem: () => {},
    removeItem: () => {},
    clear: () => {},
  },
  writable: true,
});
