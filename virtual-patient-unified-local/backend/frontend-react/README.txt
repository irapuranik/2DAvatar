This directory is NOT the React source tree.

- Run the UI from the monorepo root (sibling of backend/):
    cd ../../frontend-react
    npm install
    npm run dev

- Or from this folder (forwards to ../../frontend-react):
    npm run install-deps
    npm run dev

- `public/` here may contain generated viseme images from older paths; the backend now writes to frontend-react/public/ (see backend/config.py FRONTEND_PUBLIC_DIR).
