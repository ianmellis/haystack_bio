############################################################
# Dockerfile to build haystack_bio
# Based on Ubuntu 16.04
############################################################

# Set the base image to Ubuntu
FROM ubuntu:16.04 

# Set the working directory to /haystack_bio
WORKDIR /haystack_bio

# Copy the current directory contents into the container at /haystack_bio
COPY . /haystack_bio 

VOLUME /haystack_bio/haystack/haystack_data/genomes

ENV PATH /haystack_bio/binaries:/haystack_bio/binaries/meme/bin:$PATH

RUN apt-get update \
	&& apt-get install -y \
	python-dev \
	gfortran \
	libopenblas-dev \
	liblapack-dev \
	subversion \
	bedtools \ 
	curl \
	unzip \
	zlib1g-dev \
	default-jre \
	libexpat1-dev \
	libhtml-template-perl \
	libxml-simple-perl \
	libsoap-lite-perl \
	libxml2-dev \
	libxslt1-dev \
	python-pip \
    python-numpy \
    python-scipy\ 
    python-matplotlib \
    python-pandas \
	python-setuptools \
	&& pip install \
	bx-python \
	Jinja2 \
	pybedtools \
	tqdm \
	weblogo \
	&& cpan \
	common::sense \
	CGI::Application \
	Log::Log4perl \
	HTML::PullParser \
	HTML::Parse \
	Math::CDF JSON \
	Types::Serialiser  \
	XML::Compile::SOAP11 \
	XML::Compile::WSDL11 \
	XML::Compile::Transport::SOAPHTTP\
	&& mkdir -p /haystack_bio/binaries\
	&& curl -fL http://hgdownload.cse.ucsc.edu/admin/exe/linux.x86_64/bedGraphToBigWig \
		-o /haystack_bio/binaries/bedGraphToBigWig  \
    && chmod +x /haystack_bio/binaries/bedGraphToBigWig \
	&& curl -fL http://hgdownload.cse.ucsc.edu/admin/exe/linux.x86_64/bigWigAverageOverBed \
		-o /haystack_bio/binaries/bigWigAverageOverBed  \
    && chmod +x /haystack_bio/binaries/bigWigAverageOverBed \
	&& curl -fL  https://github.com/lomereiter/sambamba/releases/download/v0.6.6/sambamba_v0.6.6_linux.tar.bz2 \
		-o /haystack_bio/binaries/sambamba_v0.6.6_linux.tar.bz2 \
	&& tar -xvjf /haystack_bio/binaries/sambamba_v0.6.6_linux.tar.bz2 -C /haystack_bio/binaries \
	&& rm -f /haystack_bio/binaries/sambamba_v0.6.6_linux.tar.bz2 \ 
    && ln -s /haystack_bio/binaries/sambamba_v0.6.6 /haystack_bio/binaries/sambamba \
	&& curl -fL http://alternate.meme-suite.org/meme-software/4.12.0/meme_4.12.0.tar.gz \
		-o /haystack_bio/binaries/meme_4.12.0.tar.gz  \
	&& tar -xzf /haystack_bio/binaries/meme_4.12.0.tar.gz -C /haystack_bio/binaries \
	&& rm -f /haystack_bio/binaries/meme_4.12.0.tar.gz \
	&& apt-get remove -y \
	python-pip \
    curl \
	&& rm -rf /var/lib/apt/lists/*


WORKDIR /haystack_bio/binaries/meme_4.12.0 

RUN ./configure --prefix=/haystack_bio/binaries/meme \
	&& make clean \
	&& make AM_CFLAGS='-DNAN="(0.0/0.0)"' \
	&& make install \
	&& rm -rf /haystack_bio/binaries/meme_4.12.0


WORKDIR /haystack_bio

RUN python setup.py install \
	&& haystack_download_genome hg19 --yes \
	&& haystack_run_test
