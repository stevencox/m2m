export ROOT=/projects/stars
export STACK=$ROOT/stack
export PROJECT=$ROOT/m2m
export DEV=$PROJECT/dev
#export BG_HOME=$DEV/go-graphstore
export BG_HOME=/mnt/sdh1/dev/go-graphstore

export DATA_ROOT=$PROJECT/var
export MONARCH_DATA=$DATA_ROOT/monarch
export C2B2R_DATA=$DATA_ROOT/chem2bio2rdf

export PATH=$PATH:$DEV/owltools

export JAVA_HOME=$STACK/jdk/jdk1.8.0_92
export PATH=$JAVA_HOME/bin:$PATH

export BGVERSION=2.1.4
export BGJAR="jars/blazegraph-jar-$BGVERSION.jar"
export BG="java -server -XX:+UseG1GC -Xmx150g -Xms150g -cp $BGJAR com.bigdata.rdf.store.DataLoader"
export DEFAULT_GRAPH=http://m2m/

configure_m2m () {
    cd $DEV
    git clone https://github.com/geneontology/go-graphstore
    git clone git@github.com:stevencox/m2m.git
}

blazegraph () {
    cd $BG_HOME
    java -server -Xms150g -Xmx150g -Djetty.port=8899 -Djetty.overrideWebXml=conf/readonly_cors.xml -Dbigdata.propertyFile=conf/blazegraph.properties -cp jars/blazegraph-jar-2.1.4.jar:jars/jetty-servlets-9.2.3.v20140905.jar com.bigdata.rdf.sail.webapp.StandaloneNanoSparqlServer
}
blazegraph_exec () {
    set_ssd 
    cd $BG_HOME
    exec java -server -Xms200g -Xmx200g -Djetty.port=8899 -Djetty.overrideWebXml=conf/readonly_cors.xml -Dbigdata.propertyFile=conf/blazegraph.properties -cp jars/blazegraph-jar-2.1.4.jar:jars/jetty-servlets-9.2.3.v20140905.jar com.bigdata.rdf.sail.webapp.StandaloneNanoSparqlServer
}


blazeg () {

    run_loader () {
	cd $BG_HOME
	local graph=$1
	local data_directory=$2
	local namespace=""
	if [ ! -z "$3" ]; then
	    namespace="-namespace $3"
	fi
	$BG -verbose -defaultGraph $graph $namespace conf/blazegraph.properties $data_directory
    }

    load_data () {
	run_loader http://m2m/ $1
    }
    monarch () {
	fetch () {
	    cd $MONARCH_DATA
	    pwd
	    dbs="ctd biogrid clinvar ensemble go hgnc keg ncbigene omim reactome"
	    for d in $dbs; do
		echo fetching $d...
		wget --quiet --timestamping http://data.monarchinitiative.org/ttl/$d.ttl
	    done
	}
	load () {
	    load_data $MONARCH_DATA
	}
	$*
    }
    chem2bio2rdf () {
	fetch () {
	    cd $C2B2R_DATA
	    pwd
	    dbs="drugbank pubchem"
	    for d in $dbs; do
		echo fetching $d...
		wget --quiet --timestamping http://cheminfov.informatics.indiana.edu:8080//download/$d.n3.gz
	    done
	    gunzip *.gz
	}
	fix () {
	    for f in $C2B2R_DATA/*.n3; do
		echo $f
		cat $f | sed \
		    -e "s/HIV-1 PROTEASE/HIV-1_PROTEASE/g" \
		    -e "s/ACTVA 6/ACTVA_6/g" \
		    -e "s/GRESAG 4.1/GRESAG_4.1/g" \
		    -e "s/CSR 1.2/CSR_1.2/g" \
		    -e "s/ >/>/g" \
		    -e "s,pubchem/resource/drugbank_drug,drugbank/resource/drugbank_drug,g" \
		    -e "s/Not Available/Not_available/g" \
		    -e "s/Not available/Not_available/g" \
		    -e "s/GENE 7/GENE_7/g" \
		    -e "s/POU 2/POU_2/g" \
		    -e "s/ (C)/_(C)/g" \
		    > $f.new
		mv $f.new $f
	    done
	}
	load () {
	    load_data $C2B2R_DATA
	}
	$*
    }

    pcrdf () {
	PCRDF_ROOT=$DATA_ROOT/pubchemrdf
	seen=$DATA_ROOT/loaded.txt
	dirs="compound/general substance descriptor/compound descriptor/substance synonym inchikey measuregroup endpoint bioassay protein biosystem conserveddomain gene reference source concept"
	function load () {
	    for d in $dirs; do
		load_dir=$PCRDF_ROOT/$d
		echo loading $load_dir
		for archive in $load_dir/*; do
		    if [[ "$(echo $archive | grep -c 3d)" -eq 0 && "$(echo $archive | grep -c 2d)" -eq 0 ]]; then
			echo  --archive: $archive
			run_loader $DEFAULT_GRAPH $archive http://rdf.ncbi.nlm.nih.gov/pubchem/$d
		    fi
		done
	    done
	    cd $PCRDF_ROOT
	}
	$*
    }


    load () {
	set_ssd
	#pcrdf load
	load_data $DATA_ROOT/monarch
	load_data $DATA_ROOT/chem2bio2rdf
    }

    set_ssd () {
	#export DATA_ROOT=/ssdscratch/scox/var
	export BG_HOME=/ssdscratch/scox/dev/go-graphstore
	echo set ssd settings...
    }
    ssd_load () {
	set_ssd
	load $*
    }

    $*
}



