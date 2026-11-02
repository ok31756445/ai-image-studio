FROM node:22-alpine
WORKDIR /app
COPY . .
ENV IMAGE_STUDIO_HOST=0.0.0.0
ENV PORT=7860
EXPOSE 7860
CMD ["node", "offline-server.cjs", "--no-open"]
