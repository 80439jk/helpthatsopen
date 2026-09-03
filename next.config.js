/** @type {import('next').NextConfig} */
module.exports = {
  reactStrictMode: true,
  // .cursorrules URL architecture uses trailing slashes (/texas/harris-county/).
  // Next strips them by default, which 308-redirects every documented URL.
  trailingSlash: true,
};
