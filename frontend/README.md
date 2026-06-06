# React Frontend — WebMail Dashboard

A modern React single-page application (SPA) for managing transactional email through the WebMail API.

## Features

- **Authentication** — Email/password login with 2FA (TOTP) support
- **Dashboard** — Real-time email metrics with Recharts analytics
- **Domain Management** — DNS verification, SPF/DKIM/DMARC record display
- **Templates** — HTML/text email template editor with live preview
- **Messages** — View sent messages with event timeline (open/click/bounce tracking)
- **Webhooks** — Configure and test webhook endpoints
- **API Keys** — Generate and manage API authentication keys
- **Settings** — 2FA setup, password change, API key management

## Prerequisites

- **Node.js 18+** and npm 11+
- Backend API running at `http://localhost:8000` (for local development)

## Local Development Setup

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Start the development server

```bash
npm start
```

The app opens at **http://localhost:3000**

### 3. Build for production

```bash
npm run build
```

Output files are in `build/` directory.

## Environment Variables

Create a `.env` file in the `frontend/` directory (optional for local dev):

```env
REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_DOCS_URL=http://localhost:8000/api/docs
```

These are optional; the app defaults to `http://localhost:8000`.

## Project Structure

```
frontend/
├── public/              # Static HTML, favicon, manifest
├── src/
│   ├── api/            # API client and endpoint functions
│   │   ├── client.js   # Axios instance with auth interceptor
│   │   ├── auth.js     # Authentication endpoints
│   │   ├── messages.js # Message CRUD operations
│   │   ├── domains.js  # Domain management endpoints
│   │   ├── templates.js # Email template endpoints
│   │   ├── webhooks.js  # Webhook endpoints
│   │   └── stats.js     # Analytics endpoints
│   ├── components/      # Reusable React components
│   │   ├── Nav.js       # Navigation sidebar
│   │   ├── PrivateRoute.js # Protected route wrapper
│   │   ├── TestEmailButton.js # Email test dialog
│   │   ├── DnsRecordDisplay.js # DNS record UI
│   │   └── ...
│   ├── pages/          # Full page components
│   │   ├── Login.js
│   │   ├── Signup.js
│   │   ├── Dashboard.js
│   │   ├── Domains.js
│   │   ├── Templates.js
│   │   ├── Messages.js
│   │   ├── Webhooks.js
│   │   ├── Settings.js
│   │   └── ...
│   ├── App.js          # Main app component with routing
│   ├── index.js        # ReactDOM render entry point
│   └── index.css       # Global styles (Tailwind imports)
├── package.json        # Dependencies and scripts
├── tailwind.config.js  # Tailwind CSS configuration
├── postcss.config.js   # PostCSS configuration
└── README.md           # This file
```

## Available Scripts

### `npm start`
Runs the app in development mode with hot reload.
Opens http://localhost:3000

### `npm run build`
Builds the app for production to the `build/` folder.
Ready for deployment.

### `npm test`
Launches the test runner in interactive watch mode.

### `npm run eject`
**Note: this is a one-way operation.** Once you eject, you can't go back!

## Dependencies

### Core
- **react** 18.3.1 — UI framework
- **react-dom** 18.3.1 — DOM rendering
- **react-router-dom** 6.22.3 — Client-side routing

### HTTP & State Management
- **axios** 1.6.5 — HTTP client with interceptors
- **@tanstack/react-query** 5.28.0 — Server state management
- **zustand** (optional) — Client state management

### UI & Styling
- **tailwindcss** 3.4.3 — Utility-first CSS framework
- **recharts** 2.12.3 — React charting library

### Development
- **tailwindcss** — Included above
- **postcss** — CSS processing
- **autoprefixer** — CSS vendor prefixing

## API Integration

The frontend communicates with the Django REST API at `/api/v1/`.

### Authentication
All requests include an `Authorization: Bearer <token>` header set by the Axios interceptor in `src/api/client.js`.

Login flow:
1. User submits email/password to `POST /api/v1/auth/login/`
2. Backend returns `{access_token, refresh_token}`
3. Token stored in `localStorage`
4. Interceptor adds `Authorization` header to all requests

### Example API Call

```javascript
// src/api/messages.js
import client from './client';

export const fetchMessages = (params) => {
  return client.get('/messages/', { params });
};

// In a component:
import { useQuery } from '@tanstack/react-query';
import { fetchMessages } from '../api/messages';

function MessageList() {
  const { data, isLoading } = useQuery({
    queryKey: ['messages'],
    queryFn: () => fetchMessages({ limit: 10 }),
  });
  
  return isLoading ? <div>Loading...</div> : <div>{data.results.length} messages</div>;
}
```

## Styling

This project uses **Tailwind CSS** for styling. No custom CSS files are needed for most UI.

Tailwind config: `tailwind.config.js`  
PostCSS config: `postcss.config.js`  
Global imports: `src/index.css`

### Adding Tailwind Styles
Classes are applied directly in JSX:

```jsx
<button className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded">
  Click me
</button>
```

## Testing

Run the test suite:

```bash
npm test
```

Write tests in files ending with `.test.js` or `.spec.js` in the same directory as the code being tested.

Example:

```javascript
// src/api/messages.test.js
import { fetchMessages } from './messages';

describe('fetchMessages', () => {
  it('fetches messages from API', async () => {
    const data = await fetchMessages({ limit: 10 });
    expect(data.results).toBeDefined();
  });
});
```

## Troubleshooting

### "Cannot find module 'react-router-dom'"
```bash
npm install react-router-dom
```

### API requests return 401 Unauthorized
- Check that token is stored in `localStorage` after login
- Verify `Authorization` header is being sent (check Network tab in DevTools)
- Token may have expired; log out and log back in

### Tailwind classes not applying
- Ensure `npm start` is running (builds Tailwind on the fly)
- For `npm run build`, verify `postcss.config.js` includes Tailwind plugin
- Check that class names are in static strings, not template literals with variables

### Port 3000 already in use
```bash
# Windows PowerShell
Get-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess | Stop-Process

# macOS / Linux
lsof -ti:3000 | xargs kill -9
```

## Build & Deployment

The production build is optimized for performance:

```bash
npm run build
```

Then serve the `build/` folder using a static file server or Docker:

```dockerfile
FROM node:20-alpine as build
WORKDIR /app
COPY . .
RUN npm ci && npm run build

FROM nginx:latest
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Performance Tips

1. **Code Splitting** — Use `React.lazy()` and `Suspense` for route-based code splitting
2. **Memoization** — Wrap expensive components with `React.memo()`
3. **Query Caching** — Let React Query cache API responses; adjust `staleTime` as needed
4. **Image Optimization** — Compress images and use WebP format where possible
5. **Bundle Analysis** — Run `npm run build --report` to visualize bundle size

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes and test: `npm start` + `npm test`
3. Commit with clear message: `git commit -m "Add feature X"`
4. Push and create a pull request

## License

Proprietary — WebMail Platform

## Support

For issues or questions, see the main [README.md](../README.md) or contact the development team.
