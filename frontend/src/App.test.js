import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import App from "./App";

describe("App", () => {
  let originalFetch;
  let scrollMock;

  beforeEach(() => {
    originalFetch = global.fetch;

    // Mock localStorage and sessionStorage
    const localStorageMock = {
      getItem: jest.fn(() => null),
      setItem: jest.fn(),
      removeItem: jest.fn(),
      clear: jest.fn(),
    };
    const sessionStorageMock = {
      getItem: jest.fn(() => null),
      setItem: jest.fn(),
      removeItem: jest.fn(),
      clear: jest.fn(),
    };
    Object.defineProperty(window, 'localStorage', { value: localStorageMock, writable: true });
    Object.defineProperty(window, 'sessionStorage', { value: sessionStorageMock, writable: true });

    // Default: successful fetch for /api/hello and /api/bandit/variant
    global.fetch = jest.fn((url, options) => {
      const urlString = typeof url === 'string' ? url : url.url;
      
      if (urlString.includes('/api/hello')) {
        return Promise.resolve({
          json: () => Promise.resolve({ message: "Hello from mock" }),
          ok: true,
        });
      } else if (urlString.includes('/api/bandit/variant')) {
        return Promise.resolve({
          json: () => Promise.resolve({ variant: "A", stats: {} }),
          ok: true,
        });
      } else if (urlString.includes('/api/bandit/conversion')) {
        return Promise.resolve({
          json: () => Promise.resolve({ status: "recorded", variant: "A" }),
          ok: true,
        });
      } else if (urlString.includes('/api/ask')) {
        return Promise.resolve({
          json: () => Promise.resolve({ answer: "This is a mock answer" }),
          ok: true,
        });
      }
      return Promise.resolve({
        json: () => Promise.resolve({}),
        ok: true,
      });
    });

    // Mock scrollIntoView so auto-scroll effect doesn't crash
    scrollMock = jest.fn();
    window.HTMLElement.prototype.scrollIntoView = scrollMock;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.clearAllMocks();
  });

  test("renders header message from /api/hello and auto-scroll runs", async () => {
    const { container } = render(<App />);

    // /api/hello was fetched (relative URL for localhost)
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith("/api/hello");
    });

    // /api/bandit/variant was also fetched
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith("/api/bandit/variant");
    });

    // Header shows mocked message
    expect(await screen.findByText("Hello from mock")).toBeInTheDocument();

    // Once messages change, scrollIntoView should be called at least once
    await waitFor(() => {
      expect(scrollMock).toHaveBeenCalled();
    });

    // No typing indicator initially
    expect(container.querySelector(".typing-indicator")).toBeNull();
  });

  test("handles fetch error without crashing", async () => {
    const error = new Error("network down");
    global.fetch = jest.fn(() => Promise.reject(error));

    const consoleErrorSpy = jest
      .spyOn(console, "error")
      .mockImplementation(() => {});

    render(<App />);

    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalled();
    });

    // First argument should be our error label
    const [firstArg] = consoleErrorSpy.mock.calls[0];
    expect(String(firstArg)).toContain("Error fetching /api/hello:");
    consoleErrorSpy.mockRestore();
  });

  test("sends message via REST API and displays response", async () => {
    render(<App />);

    // Wait for initial fetches to complete
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith("/api/hello");
    });

    const input = screen.getByPlaceholderText("Ask something...");
    const sendButton = screen.getByText("Send");

    // Type a message
    fireEvent.change(input, { target: { value: "Hello   " } });
    expect(sendButton).not.toBeDisabled();

    // Clear previous fetch calls
    jest.clearAllMocks();

    // Click send button
    fireEvent.click(sendButton);

    // User message should be visible
    expect(await screen.findByText("Hello")).toBeInTheDocument();

    // Should call /api/ask with POST
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/ask",
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: "Hello" }),
        })
      );
    });

    // Should also call /api/bandit/conversion
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/bandit/conversion",
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ variant: "A" }),
        })
      );
    });

    // Wait for AI response to appear
    expect(await screen.findByText("This is a mock answer")).toBeInTheDocument();

    // Input should be cleared
    expect(input.value).toBe("");
  });

  test("send button is disabled with empty input and Enter key sends", async () => {
    render(<App />);

    // Wait for initial fetches
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith("/api/hello");
    });

    const input = screen.getByPlaceholderText("Ask something...");
    const sendButton = screen.getByText("Send");

    // Initially disabled (no input)
    expect(sendButton).toBeDisabled();

    // Type something
    fireEvent.change(input, { target: { value: "Hi there" } });
    expect(sendButton).not.toBeDisabled();

    // Clear previous fetch calls
    jest.clearAllMocks();

    // Use Enter key (without shift) to send
    fireEvent.keyPress(input, {
      key: "Enter",
      code: "Enter",
      charCode: 13,
      shiftKey: false,
    });

    // Should call /api/ask
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/ask",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ question: "Hi there" }),
        })
      );
    });

    // Input cleared after sending
    expect(input.value).toBe("");
  });

  test("handles REST API error gracefully", async () => {
    // Mock /api/ask to fail
    global.fetch = jest.fn((url) => {
      if (typeof url === 'string' && url.includes('/api/ask')) {
        return Promise.reject(new Error("API error"));
      } else if (typeof url === 'string' && url.includes('/api/hello')) {
        return Promise.resolve({
          json: () => Promise.resolve({ message: "Hello from mock" }),
          ok: true,
        });
      } else if (typeof url === 'string' && url.includes('/api/bandit/variant')) {
        return Promise.resolve({
          json: () => Promise.resolve({ variant: "A", stats: {} }),
          ok: true,
        });
      }
      return Promise.resolve({
        json: () => Promise.resolve({}),
        ok: true,
      });
    });

    const consoleErrorSpy = jest
      .spyOn(console, "error")
      .mockImplementation(() => {});

    render(<App />);

    // Wait for initial setup
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith("/api/hello");
    });

    const input = screen.getByPlaceholderText("Ask something...");
    const sendButton = screen.getByText("Send");

    fireEvent.change(input, { target: { value: "Test question" } });
    
    // Clear previous fetch calls
    jest.clearAllMocks();

    fireEvent.click(sendButton);

    // Should show error message
    await waitFor(() => {
      expect(screen.getByText(/Sorry, I ran into an error/i)).toBeInTheDocument();
    });

    // Should have logged the error
    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalled();
    });

    consoleErrorSpy.mockRestore();
  });

  test("shows thinking state while waiting for response", async () => {
    let resolveAsk;
    const askPromise = new Promise((resolve) => {
      resolveAsk = resolve;
    });

    global.fetch = jest.fn((url) => {
      if (typeof url === 'string' && url.includes('/api/ask')) {
        return askPromise;
      } else if (typeof url === 'string' && url.includes('/api/hello')) {
        return Promise.resolve({
          json: () => Promise.resolve({ message: "Hello from mock" }),
          ok: true,
        });
      } else if (typeof url === 'string' && url.includes('/api/bandit/variant')) {
        return Promise.resolve({
          json: () => Promise.resolve({ variant: "A", stats: {} }),
          ok: true,
        });
      } else if (typeof url === 'string' && url.includes('/api/bandit/conversion')) {
        return Promise.resolve({
          json: () => Promise.resolve({ status: "recorded", variant: "A" }),
          ok: true,
        });
      }
      return Promise.resolve({
        json: () => Promise.resolve({}),
        ok: true,
      });
    });

    const { container } = render(<App />);

    // Wait for initial setup
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith("/api/hello");
    });

    const input = screen.getByPlaceholderText("Ask something...");
    const sendButton = screen.getByText("Send");

    fireEvent.change(input, { target: { value: "Test" } });
    
    // Clear previous fetch calls
    jest.clearAllMocks();

    fireEvent.click(sendButton);

    // Button should show "Thinking..." while waiting
    await waitFor(() => {
      expect(screen.getByText("Thinking...")).toBeInTheDocument();
    });

    // Button should be disabled while thinking
    expect(sendButton).toBeDisabled();

    // Resolve the promise
    resolveAsk({
      json: () => Promise.resolve({ answer: "Answer here" }),
      ok: true,
    });

    // Wait for response and button to return to normal
    await waitFor(() => {
      expect(screen.getByText("Send")).toBeInTheDocument();
    });
  });
});
