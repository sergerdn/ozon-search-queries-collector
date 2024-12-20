(async () => {
  class UnauthorizedError extends Error {
    constructor(message) {
      super(message);
      this.name = "UnauthorizedError";
    }
  }

  class ForbiddenError extends Error {
    constructor(message) {
      super(message);
      this.name = "ForbiddenError";
    }
  }

  class RateLimitError extends Error {
    constructor(message) {
      super(message);
      this.name = "RateLimitError";
    }
  }

  async function parallelPaginateRequests(keyword_query, maxRetries) {
    const baseURL = "https://data.ozon.ru/api/searchstat_analytics/queries_search";
    const headers = {
      accept: "application/json, text/plain, */*",
      "cache-control": "no-cache",
      "content-type": "application/json",
      pragma: "no-cache",
      "sec-fetch-dest": "empty",
      "sec-fetch-mode": "cors",
      "sec-fetch-site": "same-origin",
      "x-o3-app-name": "exa-ui",
      "x-o3-app-version": "release/EXAR-797_835",
      "x-o3-language": "ru",
    };

    const paginationLimit = 50; // Number of items per page
    let totalItems = null; // Total items determined from the first response
    const capturedData = []; // Array to store all results

    console.log("[Timing] Data harvesting started.");
    const startTime = performance.now();

    // Function to retry a request if it fails
    async function fetchWithRetry(requestBody, retriesLeft = maxRetries) {
      try {
        const response = await fetch(baseURL, {
          method: "POST",
          headers,
          body: requestBody,
          credentials: "include",
        });

        if (response.status === 401) {
          throw new UnauthorizedError("Request blocked: Unauthorized (401)");
        }
        if (response.status === 403) {
          throw new ForbiddenError("Request blocked: Forbidden (403)");
        }
        if (response.status === 429) {
          throw new RateLimitError("Request limited: Too Many Requests (429)");
        }

        if (!response.ok) {
          throw new Error(`Request failed with status: ${response.status}`);
        }

        return await response.json();
      } catch (error) {
        if (error instanceof UnauthorizedError || error instanceof ForbiddenError || error instanceof RateLimitError) {
          console.error(`[Abort] ${error.message}`);
          throw error;
        }

        if (retriesLeft > 0) {
          console.warn(`[Retry] Request failed. Retrying... (${maxRetries - retriesLeft + 1}/${maxRetries})`);
          return fetchWithRetry(requestBody, retriesLeft - 1);
        } else {
          console.error(`[Error] Request failed after ${maxRetries} retries.`);
          throw error; // Throw error if retries are exhausted
        }
      }
    }

    try {
      // Step 1: Make the first request to get total items
      const initialRequestBody = JSON.stringify({
        limit: paginationLimit.toString(),
        offset: "0",
        text: keyword_query,
        sorting: { order: "desc", attribute: "count" },
      });

      const initialData = await fetchWithRetry(initialRequestBody);
      totalItems = parseInt(initialData.total, 10);
      console.log(`[Info] Total items to fetch: ${totalItems}, for "${keyword_query}"`);

      // Step 2: Generate all offset-based requests
      const totalRequests = Math.ceil(totalItems / paginationLimit);
      const requests = Array.from({ length: totalRequests }, (_, i) => {
        const offset = i * paginationLimit;
        const requestBody = JSON.stringify({
          limit: paginationLimit.toString(),
          offset: offset.toString(),
          text: keyword_query,
          sorting: { order: "desc", attribute: "count" },
        });

        return fetchWithRetry(requestBody); // Use fetchWithRetry for parallel requests
      });

      console.log(`[Info] Starting ${totalRequests} parallel requests.`);

      // Step 3: Execute all requests in parallel
      const responses = await Promise.allSettled(requests);

      // Step 4: Process successful responses
      for (const response of responses) {
        if (response.status === "fulfilled") {
          capturedData.push(...response.value.data);
        } else {
          console.error("[Error] Failed request in parallel execution:", response.reason);
        }
      }
    } catch (error) {
      console.error("[Error] Failed during data harvesting:", error);
      throw error; // Propagate the error for higher-level handling
    }

    const endTime = performance.now();

    console.log("[Timing] Data harvesting completed.");
    console.log(`[Timing] Total time: ${((endTime - startTime) / 1000).toFixed(2)}s.`);
    console.log("Pagination completed.");

    return capturedData;
  }

  const keywordQuery = "коктейльное платье";
  const maxRetries = 5;

  try {
    const capturedData = await parallelPaginateRequests(keywordQuery, maxRetries);
    console.log("All captured data:", JSON.stringify(capturedData));

    return capturedData;
  } catch (error) {
    if (error instanceof UnauthorizedError) {
      console.error("Process terminated: Unauthorized access.");
    } else if (error instanceof ForbiddenError) {
      console.error("Process terminated: Access forbidden.");
    } else {
      console.error("Unexpected error:", error.message);
    }
  }
})();
