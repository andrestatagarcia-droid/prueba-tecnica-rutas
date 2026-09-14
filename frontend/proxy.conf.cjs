const target = process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000';

module.exports = {
  '/api': {
    target,
    secure: false,
    changeOrigin: true,
  },
};