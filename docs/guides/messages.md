# Messages

The SDK has no hardcoded user facing text. Every error message, every validation message and the help text of every setting lives in one YAML file inside the package, `binaaz_sdk/messages.yaml`. You can replace some or all of them at runtime, for example to show errors in Azerbaijani in your own product.

## Replace a few messages

```python
from binaaz_sdk import messages

messages.use({
    "value.photos": "bina.az elanda {low} ilə {high} arasında şəkil qəbul edir, {count} göndərildi",
    "error.session": "bina.az sessiyanı qəbul etmədi. Yenidən daxil olun",
})
```

Keys are the dotted paths in the YAML file. A nested mapping works too:

```python
messages.use({"error": {"session": "bina.az sessiyanı qəbul etmədi. Yenidən daxil olun"}})
```

## Load a whole file

```yaml
value:
  empty: "{field} boş ola bilməz"
  photos: "bina.az elanda {low} ilə {high} arasında şəkil qəbul edir, {count} göndərildi"
error:
  session: bina.az sessiyanı qəbul etmədi. Yenidən daxil olun
  blocked: "{host} Cloudflare yoxlama səhifəsi qaytardı."
```

```python
messages.use("messages.az.yaml")
```

The file only needs the keys you want to change; the rest keep their defaults.

## Rules

- An unknown key raises `KeyError` naming it. A typo fails at once instead of being ignored.
- Keep the `{placeholders}` of the original message. They are filled with `str.format`, and a missing one raises `KeyError` when the message is used.
- `messages.use` changes the messages for the whole process, for every client.
- `messages.reset()` goes back to the defaults.

## See every key

```python
from binaaz_sdk import messages

for key, value in sorted(messages.catalog().items()):
    print(key, "=", value)
```

`messages.text(key, **params)` returns one message with its placeholders filled, the same way the SDK does.

The keys are grouped:

| Group | Used for |
| --- | --- |
| `settings.*` | The description of each setting |
| `value.*` | Arguments refused before sending (`InvalidRequestError`) |
| `error.*` | Errors from bina.az, the network and the SMS login service |

The full default file is in the repository: [src/binaaz_sdk/messages.yaml](https://github.com/qiyascc/binaaz-python-sdk/blob/main/src/binaaz_sdk/messages.yaml).
