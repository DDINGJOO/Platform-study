rootProject.name = "co3"

plugins {
    // dependency-analysis 플러그인을 빌드 전체에 건다 (buildHealth)
    id("com.autonomousapps.build-health") version "3.19.2"
}

include("m1")
include("m2")
include("m3")
include("m4")
include("m5")
include("an")
include("an-decl")
