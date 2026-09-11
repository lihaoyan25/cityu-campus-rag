# 多阶段构建: node 构建 → nginx 托管静态文件
FROM node:20-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN npm install --registry=https://registry.npmmirror.com

COPY . .
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
