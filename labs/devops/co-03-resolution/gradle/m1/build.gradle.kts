plugins {
    application
}

val bVersion = (findProperty("bVersion") ?: "1.0").toString()

dependencies {
    implementation("lab.co3:a:1.0")
    implementation("lab.co3:b:$bVersion")
}

application {
    mainClass.set("lab.co3.Main")
}
