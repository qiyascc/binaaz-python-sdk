# FAQ and troubleshooting

## Is this an official bina.az API?

No. bina.az does not publish an API for agencies. The SDK talks to the same endpoints the bina.az website uses, as one signed in account, and identifies itself with its own User-Agent. bina.az can change those endpoints at any time; every address and path is a setting, so a change can often be followed with configuration until a new release is out.

## Every call raises `BlockedError`

bina.az answered with a Cloudflare challenge page. The SDK does not solve challenges. It usually depends on the network the code runs from: data center addresses are challenged more often than home or office connections. Try from another network. Slowing down helps too, if you send many requests.

## `AuthenticationError` right after signing in

The sign in worked but the session was refused on the next call. Check that:

- you are not mixing two clients, one signed in and one not;
- the cookie you saved is the one from `bina.cookie` after the sign in, not before;
- the system clock is right, since expired cookies are judged by date.

## `NotSupportedError: Listing management needs a bina.az company profile`

`items.list` and `items.all` work for company profiles (agencies and residences). A private account cannot list its listings through this API.

## `ItemError` with status `RESTRICTED`

bina.az wants the account's phone number confirmed before it accepts listings. Confirm it on the website, then post again.

## `InvalidRequestError: bina.az takes 4 to 30 photos on a listing`

The listing has fewer than 4 or more than 30 photo ids. Upload more photos, or trim the list.

## Two SMS messages arrived

The login service did not give a usable answer the first time, so the SDK asked again; `CodeSent.retried` was `True`. Use the code from the latest SMS.

## The code is refused although it is right

If the check had to be repeated, the first attempt may already have used the code. Ask for a new one with `send_code`.

## `OutcomeUnknownError` on `create`

The request was sent but no answer came back. The listing may exist. Look at the pending tab (`bina.items.list("pending")`) before posting again. See [Safety and retries](../guides/safety.md#when-the-outcome-is-unknown).

## `ConfigurationError: Refusing to send a session over plain http`

One of the addresses in the settings starts with `http://` and is not localhost. Use https, or set `allow_insecure_http=True` for a test server on a private network.

## A config file is ignored

The file must be in the working directory with one of the names `binaaz.toml`, `binaaz.yaml`, `binaaz.yml` or `binaaz.json`, or be named in `BINAAZ_CONFIG` or `config_file=`. YAML needs the `yaml` extra, TOML on Python 3.10 the `toml` extra. Environment variables and arguments in code win over the file.

## How do I see what is sent?

Pass an `httpx.Client` with an event hook that logs the method, path and status; see [Advanced use](../guides/advanced.md#your-own-httpx-client). Do not log headers, they contain the session cookie.

## Can I use it from several threads?

Yes for reads on one client. Do not sign in on a client while other threads use it. Give each account its own client.

## Is there rate limiting?

bina.az answers 429 when it gets too many requests. The SDK waits for the time bina.az asks (up to `backoff_cap`) and tries again. Keep parallel requests modest, especially with the async client.
