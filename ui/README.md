# TAK Module Federation Component

## Development

While the federated component works both in rmlocal and rmdev, it is recommended to seperately develop the component. This is partly because the federated component is only built when rmlocal/rmdev is built and hence doesn't currently update in real time.

**Install dependencies and start the dev server**

```bash
pnpm install
pnpm dev
```

Component runs locally at: [http://localhost:4174/](http://localhost:4174/)

## Assets

Place assets in the `public/` folder, for example:

```
public/taistelija.png
```

When using these assets in code **always** prefix them with `/ui/{shortProductName}/`. for example:

```
/ui/tak/taistelija.png
```

This is required due to how things are included in the production. `vite.config.ts` rewrites the routes for local development.



## Sample Data

For developing components it is recommended to manually fetch the user data from the api, for example:

```
https://localmaeher.dev.pvarki.fi:4439/api/v2/instructions/data/tak
```

Paste the entire response into `src/main.tsx` as the value of `SAMPLE_DATA`.

It is recommended to test what happens if no data is passed.

## Styles

`src/index.css` should reflect the styles of the main UI. It could be outdated, so it might be worth while to copy the file from the main UI here every once in a while.

This file is **not** included in the production build. It is only used to make local development possible. In production the styles of main UI are used.