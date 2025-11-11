# Step 1: Use an official Nginx base image from the Docker Hub
FROM nginx:alpine

# Step 2: Copy all files from the current directory to the Nginx default public folder
COPY . /usr/share/nginx/html

# Step 3: Expose port 80 to the outside world
EXPOSE 80

# Step 4: Start Nginx when the container launches
CMD ["nginx", "-g", "daemon off;"]
