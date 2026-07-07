# WordPress image for the Reeldrive Pro shop

This folder only exists to fix one thing: the stock Railway "WordPress + MySQL"
template doesn't include the **ionCube Loader**, which the BalePay plugin (and
most commercial rtl-theme.com plugins) need to run.

## Switch your Railway WordPress service to build from here

1. In Railway, open the **Docker Image** service (the one currently running
   WordPress) → **Settings** → **Source**.
2. Change the source from "Docker Image" to **GitHub Repo** → select
   `parsaforughi/reeldrive`.
3. Set **Root Directory** to `wordpress`.
4. Builder should auto-detect as **Dockerfile**. If not, set it manually.
5. Keep the existing **Volume** mounted at `/var/www/html` (don't remove it —
   that's where your WordPress files/uploads live) and keep the same
   `WORDPRESS_DB_*` variables pointing at the MySQL service.
6. Deploy. Check the build logs — you should see the ionCube download step
   run, then Apache start normally.
7. Re-activate the BalePay plugin. The ionCube error should be gone.

If your Railway service happens to run on ARM instead of x86-64 (unlikely for
a standard Railway deploy, but possible), edit `Dockerfile` in this folder and
swap the ionCube download URL for the `aarch64` build (linked in a comment in
the Dockerfile).
