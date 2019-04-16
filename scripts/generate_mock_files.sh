#!/bin/sh
# This file generates the JSON enrollment data files for
# the V1 mock API. It deletes any existing JSON files.
# Run this from the root directory of Registrar:
# $ scripts/generate_mock_files.sh

DATA_PATH=registrar/static/api/v1_mock
PGM_DATA_PATH=$DATA_PATH/program-enrollments
CRS_DATA_PATH=$DATA_PATH/course-enrollments
PGM_ENROLLS=scripts/fake_program_enrollments.py
CRS_ENROLLS=scripts/fake_course_enrollments.py

rm -rf $PGM_DATA_PATH
mkdir -p $PGM_DATA_PATH
rm -rf $CRS_DATA_PATH
mkdir -p $CRS_DATA_PATH

$PGM_ENROLLS 100 10 donnaview.edu > $PGM_DATA_PATH/polysci.json
$CRS_ENROLLS 50 $PGM_DATA_PATH/polysci.json > $CRS_DATA_PATH/polysci-comm-101.json
$CRS_ENROLLS 30 $PGM_DATA_PATH/polysci.json > $CRS_DATA_PATH/polysci-gov-200.json
$CRS_ENROLLS 20 $PGM_DATA_PATH/polysci.json > $CRS_DATA_PATH/polysci-gov-201.json
$CRS_ENROLLS 10 $PGM_DATA_PATH/polysci.json > $CRS_DATA_PATH/polysci-gov-202.json

$PGM_ENROLLS 30 10 donnaview.edu > $PGM_DATA_PATH/mba.json
$CRS_ENROLLS 20 $PGM_DATA_PATH/mba.json > $CRS_DATA_PATH/mba-comm-101.json
$CRS_ENROLLS 15 $PGM_DATA_PATH/mba.json > $CRS_DATA_PATH/mba-biz-200.json

$PGM_ENROLLS 10 10 holmeshaven.edu > $PGM_DATA_PATH/ce.json
$CRS_ENROLLS 8 $PGM_DATA_PATH/ce.json > $CRS_DATA_PATH/ce-ma-101.json
$CRS_ENROLLS 8 $PGM_DATA_PATH/ce.json > $CRS_DATA_PATH/ce-ma-102.json
$CRS_ENROLLS 4 $PGM_DATA_PATH/ce.json > $CRS_DATA_PATH/ce-ce-300-spring.json
$CRS_ENROLLS 4 $PGM_DATA_PATH/ce.json > $CRS_DATA_PATH/ce-ce-300-summer.json

$PGM_ENROLLS 0 10 holmeshaven.edu > $PGM_DATA_PATH/physics.json
$CRS_ENROLLS 0 $PGM_DATA_PATH/physics.json > $CRS_DATA_PATH/physics-ma-101.json
$CRS_ENROLLS 0 $PGM_DATA_PATH/physics.json > $CRS_DATA_PATH/physics-ma-102.json
