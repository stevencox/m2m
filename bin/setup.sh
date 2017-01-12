export ROOT=/projects/stars
export STACK=$ROOT/stack
export PROJECT=$ROOT/m2m
export DEV=$PROJECT/dev
export BG_HOME=$DEV/go-graphstore

export PATH=$PATH:$DEV/owltools

export JAVA_HOME=$STACK/jdk/jdk1.8.0_92
export PATH=$JAVA_HOME/bin:$PATH

configure_m2m () {
    cd $DEV
    git clone https://github.com/geneontology/go-graphstore
    git clone git@github.com:stevencox/m2m.git
}

blazegraph () {
    cd $BG_HOME
    java -server -Xmx32g -Djetty.port=8899 -Djetty.overrideWebXml=conf/readonly_cors.xml -Dbigdata.propertyFile=conf/blazegraph.properties -cp jars/blazegraph-jar-2.1.4.jar:jars/jetty-servlets-9.2.3.v20140905.jar com.bigdata.rdf.sail.webapp.StandaloneNanoSparqlServer
}

