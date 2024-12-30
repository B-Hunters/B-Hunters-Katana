# Build Stage
FROM golang:1.21.1 AS build

# Install Go tools
RUN CGO_ENABLED=1 go install github.com/projectdiscovery/katana/cmd/katana@latest
 
    
# Runtime Stage (final smaller image using Python slim)
FROM python:3.12-slim

# Copy Go binaries and tools from the build stage
COPY --from=build /usr/local/go /usr/local/go
COPY --from=build /go/bin/ /root/go/bin
RUN apt update &&  apt install zip curl wget git chromium -y && apt clean && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir b-hunters==1.1.13

# Set environment variables for Go
ENV PATH="$PATH:/usr/local/go/bin:/root/go/bin:/usr/local/go/bin:$HOME/.local/bin"
ENV GOROOT="/usr/local/go"
ENV GOPATH="/root/go"


# Copy necessary files
COPY katanam katanam

# Default command
CMD ["python3", "-m", "katanam"]
