// "Too many tries": the seconds the node asked for, counting down, so a form
// stays disabled until the node will listen again (5c.3b).
// Record: docs/build-records/2026-11-11-5c3b-claim-and-sign-in.md
export class Wait {
  seconds = $state(0);
  #timer: ReturnType<typeof setInterval> | undefined;

  get active(): boolean {
    return this.seconds > 0;
  }

  start(seconds: number): void {
    this.stop();
    this.seconds = seconds;
    this.#timer = setInterval(() => {
      this.seconds -= 1;
      if (this.seconds <= 0) this.stop();
    }, 1000);
  }

  stop(): void {
    if (this.#timer !== undefined) clearInterval(this.#timer);
    this.#timer = undefined;
    if (this.seconds < 0) this.seconds = 0;
  }
}
