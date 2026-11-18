# Build Stage
FROM golang:1.26 AS build

# Install Go tools
RUN CGO_ENABLED=0 go install github.com/projectdiscovery/katana/cmd/katana@v1.8.0
 
    
# Runtime Stage (final smaller image using Python slim)
FROM python@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

# Copy Go binaries and tools from the build stage
COPY --from=build /go/bin/ /root/go/bin
RUN apt update &&  apt install zip curl wget git chromium -y && apt clean && rm -rf /var/lib/apt/lists/*
# The shared class is built from this repository, not from the published
# release: a worker that calls auth_headers(task) against a release that
# does not have it fails inside the scan.  scripts/build_workers.sh passes
# the local wheel; the default is the published release.
ARG B_HUNTERS_WHEEL=b-hunters==1.5.1
RUN pip install --no-cache-dir ${B_HUNTERS_WHEEL}

# Set environment variables for Go
ENV PATH="$PATH:/usr/local/go/bin:/root/go/bin:/usr/local/go/bin:$HOME/.local/bin"
ENV GOROOT="/usr/local/go"
ENV GOPATH="/root/go"


# Copy necessary files
COPY katanam katanam

# Default command
CMD ["python3", "-m", "katanam"]
