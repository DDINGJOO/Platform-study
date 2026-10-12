plugins {
    application
}

val bVersion = (findProperty("bVersion") ?: "1.0").toString()

dependencies {
    implementation("lab.co3:a:1.0")
    implementation("lab.co3:b:$bVersion")
    implementation("lab.co3:c:2.0")
}

application {
    mainClass.set("lab.co3.Main")
}
