plugins {
    application
}

val bVersion = (findProperty("bVersion") ?: "1.0").toString()

dependencies {
    implementation("lab.co3:b:$bVersion")
    implementation("lab.co3:e:1.0")
    implementation("lab.co3:drv:1.0")
    implementation("lab.co3:konst:1.0")
}

application {
    mainClass.set("lab.co3.Main")
}
