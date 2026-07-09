// The default CTA is an honest mailto link (baked into the HTML). When a
// collection endpoint exists (Formspree/Buttondown-style POST), configure it
// at build time with VITE_WAITLIST_ENDPOINT and this swaps in an inline form.

export function initWaitlist(): void {
  const endpoint = import.meta.env.VITE_WAITLIST_ENDPOINT as string | undefined;
  if (!endpoint) return;

  const host = document.querySelector<HTMLElement>("[data-waitlist]");
  if (!host) return;

  const form = document.createElement("form");
  form.className = "waitlist-form";
  form.action = endpoint;
  form.method = "POST";
  form.noValidate = false;
  form.innerHTML = `
    <label class="sr-only" for="waitlist-email">Email address</label>
    <input id="waitlist-email" name="email" type="email" required
           autocomplete="email" placeholder="you@example.com" />
    <button class="button" type="submit">Request early access</button>
    <p class="caption waitlist-status" role="status" aria-live="polite"></p>
  `;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const status = form.querySelector<HTMLElement>(".waitlist-status")!;
    const email = form.querySelector<HTMLInputElement>("input")!.value;
    status.dataset.state = "";
    status.textContent = "One moment.";
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!res.ok) throw new Error(String(res.status));
      status.dataset.state = "ok";
      status.textContent = "You are on the list. We will write when it is your turn.";
      form.querySelector("input")!.value = "";
    } catch {
      status.dataset.state = "error";
      status.textContent = "That did not go through. Email info@labyrinth.vision instead.";
    }
  });

  host.replaceChildren(form);
}
